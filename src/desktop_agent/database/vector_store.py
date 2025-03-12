import sqlite3
import torch
import numpy as np
from typing import List, Dict, Any, Optional
import json
import logging
from pathlib import Path
import chromadb
from chromadb.config import Settings
import time
from contextlib import asynccontextmanager
import queue
import threading
import asyncio
import shutil
from datetime import datetime
from src.monitoring.hardware_monitor import HardwareMonitor
from src.exceptions import VectorStoreError, ValidationError, DatabaseError, ChromaDBError, ConnectionError

class ConnectionPool:
    """データベース接続プール"""
    def __init__(self, db_path: str, max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self.connections = queue.Queue(maxsize=max_connections)
        self.lock = threading.Lock()
        self._fill_pool()
        
    def _fill_pool(self):
        """接続プールの初期化"""
        for _ in range(self.max_connections):
            conn = sqlite3.connect(
                self.db_path,
                isolation_level='EXCLUSIVE',
                check_same_thread=False
            )
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self.connections.put(conn)
            
    async def get_connection(self):
        """接続の非同期取得"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.connections.get)
        
    async def return_connection(self, conn):
        """接続の非同期返却"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.connections.put, conn)
        
    async def close_all(self):
        """全接続の非同期クローズ"""
        with self.lock:
            while not self.connections.empty():
                conn = await self.get_connection()
                conn.close()

class VectorStoreError(Exception):
    """ベクトルストアの基本例外クラス"""
    pass

class ValidationError(VectorStoreError):
    """入力値検証エラー"""
    pass

class DatabaseError(VectorStoreError):
    """データベース操作エラー"""
    pass

class ChromaDBError(VectorStoreError):
    """ChromaDB操作エラー"""
    pass

class ConnectionError(VectorStoreError):
    """接続エラー"""
    pass

class VectorStoreMetrics:
    """ベクトルストアのメトリクス"""
    def __init__(self):
        self.total_embeddings = 0
        self.total_queries = 0
        self.query_latencies = []
        self.insert_latencies = []
        self.update_latencies = []
        self.delete_latencies = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.error_count = 0
        self.last_vacuum_time = None
        self.db_size = 0
        self.chroma_size = 0
        
    def to_dict(self) -> Dict[str, Any]:
        """メトリクスを辞書形式で取得"""
        return {
            "total_embeddings": self.total_embeddings,
            "total_queries": self.total_queries,
            "avg_query_latency": np.mean(self.query_latencies) if self.query_latencies else 0,
            "avg_insert_latency": np.mean(self.insert_latencies) if self.insert_latencies else 0,
            "avg_update_latency": np.mean(self.update_latencies) if self.update_latencies else 0,
            "avg_delete_latency": np.mean(self.delete_latencies) if self.delete_latencies else 0,
            "cache_hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            "error_rate": self.error_count / (self.total_queries + self.total_embeddings) if (self.total_queries + self.total_embeddings) > 0 else 0,
            "db_size": self.db_size,
            "chroma_size": self.chroma_size
        }

class VectorStore:
    """ベクトルストアクラス"""
    def __init__(self, db_path: str, collection_name: str = "agent_vectors"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # メトリクスの初期化
        self.metrics = VectorStoreMetrics()
        self.metrics_lock = asyncio.Lock()
        
        # 接続プールの初期化
        try:
            self.pool = ConnectionPool(str(self.db_path))
        except Exception as e:
            raise ConnectionError(f"接続プールの初期化に失敗: {e}")
            
        self.logger = logging.getLogger(__name__)
        
        # SQL文の定義
        self.sql_statements = {
            'insert_metadata': "INSERT INTO vector_metadata (chroma_id, metadata) VALUES (?, ?)",
            'select_metadata': "SELECT metadata FROM vector_metadata WHERE chroma_id = ?",
            'update_metadata': "UPDATE vector_metadata SET metadata = ? WHERE chroma_id = ?",
            'delete_metadata': "DELETE FROM vector_metadata WHERE chroma_id = ?",
            'get_db_size': "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
        }
        
        try:
            # ChromaDB設定
            self.chroma_client = chromadb.Client(Settings(
                persist_directory=str(self.db_path.parent / "chroma")
            ))
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name
            )
            
            # データベースの初期化
            with self.pool.get_connection() as conn:
                self._initialize_db(conn)
                
            # 初期メトリクスの収集
            asyncio.create_task(self._update_metrics())
            
            # ハードウェアモニタリングの初期化
            self.hardware_monitor = HardwareMonitor()
            
            # 定期的なメトリクス更新タスクの開始
            self._start_monitoring_task()
            
        except chromadb.errors.ChromaError as e:
            raise ChromaDBError(f"ChromaDBの初期化に失敗: {e}")
        except sqlite3.Error as e:
            raise DatabaseError(f"データベースの初期化に失敗: {e}")
        except Exception as e:
            raise VectorStoreError(f"初期化エラー: {e}")
            
    @asynccontextmanager
    async def get_connection(self):
        """データベース接続の非同期取得"""
        conn = await self.pool.get_connection()
        try:
            yield conn
        finally:
            await self.pool.return_connection(conn)
            
    def _initialize_db(self, conn: sqlite3.Connection) -> None:
        """データベースの初期化"""
        try:
            cursor = conn.cursor()
            
            # インデックス付きのテーブル作成
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS vector_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chroma_id TEXT NOT NULL UNIQUE,
                metadata TEXT NOT NULL CHECK(json_valid(metadata)),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT valid_chroma_id CHECK(length(chroma_id) > 0)
            )
            """)
            
            # インデックスの作成
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chroma_id 
            ON vector_metadata(chroma_id)
            """)
            
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON vector_metadata(created_at)
            """)
            
            # トリガーの作成
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_timestamp 
            AFTER UPDATE ON vector_metadata
            BEGIN
                UPDATE vector_metadata 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END;
            """)
            
            conn.commit()
            
        except sqlite3.Error as e:
            self.logger.error(f"テーブル作成エラー: {e}")
            conn.rollback()
            raise
            
    def _validate_embedding(self, embedding: torch.Tensor) -> None:
        """埋め込みベクトルの検証"""
        try:
            if not isinstance(embedding, torch.Tensor):
                raise ValidationError("embeddingはtorch.Tensorである必要があります")
            if embedding.dim() != 2:
                raise ValidationError("embeddingは2次元テンソルである必要があります")
            if torch.isnan(embedding).any():
                raise ValidationError("embeddingにNaN値が含まれています")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"埋め込みベクトルの検証に失敗: {e}")
            
    def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
        """メタデータの検証"""
        try:
            if not isinstance(metadata, dict):
                raise ValidationError("メタデータは辞書形式である必要があります")
            if not metadata:
                raise ValidationError("メタデータが空です")
            try:
                # JSONとしての妥当性チェック
                json.dumps(metadata)
            except (TypeError, ValueError) as e:
                raise ValidationError(f"メタデータがJSON形式ではありません: {e}")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"メタデータの検証に失敗: {e}")
            
    def _validate_embedding_id(self, embedding_id: str) -> None:
        """埋め込みIDの検証"""
        try:
            if not isinstance(embedding_id, str):
                raise ValidationError("embedding_idは文字列である必要があります")
            if not embedding_id.startswith("vec_"):
                raise ValidationError("embedding_idは'vec_'で始まる必要があります")
            if not embedding_id[4:].isdigit():
                raise ValidationError("embedding_idの形式が不正です")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"埋め込みIDの検証に失敗: {e}")
            
    @asynccontextmanager
    async def transaction(self):
        """トランザクションコンテキストマネージャー"""
        async with self.get_connection() as conn:
            try:
                conn.execute("BEGIN EXCLUSIVE")
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise
                
    async def _update_metrics(self):
        """メトリクスの更新"""
        try:
            async with self.metrics_lock:
                # データベースサイズの取得
                async with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(self.sql_statements['get_db_size'])
                    self.metrics.db_size = cursor.fetchone()[0]
                    
                # ChromaDBサイズの取得
                chroma_dir = self.db_path.parent / "chroma"
                self.metrics.chroma_size = sum(
                    f.stat().st_size for f in chroma_dir.glob('**/*')
                    if f.is_file()
                )
                
                # 総埋め込み数の更新
                collection_stats = self.collection.get()
                self.metrics.total_embeddings = len(collection_stats["ids"])
                
        except Exception as e:
            self.logger.error(f"メトリクス更新エラー: {e}")
            
    async def get_metrics(self) -> Dict[str, Any]:
        """メトリクスの取得"""
        await self._update_metrics()
        return self.metrics.to_dict()
        
    async def add_embedding(self, embedding: torch.Tensor,
                         metadata: Dict[str, Any]) -> None:
        """埋め込みベクトルの追加"""
        start_time = time.time()
        try:
            # 入力値の検証
            self._validate_embedding(embedding)
            self._validate_metadata(metadata)
            
            # 埋め込みIDの生成と検証
            embedding_id = f"vec_{int(time.time()*1000)}"
            self._validate_embedding_id(embedding_id)
            
            # ChromaDBに追加
            embedding_numpy = embedding.cpu().numpy()
            if not np.isfinite(embedding_numpy).all():
                raise ValidationError("埋め込みベクトルに無限大または非数値が含まれています")
                
            try:
                self.collection.add(
                    embeddings=embedding_numpy.tolist(),
                    documents=[json.dumps(metadata)],
                    ids=[embedding_id]
                )
            except chromadb.errors.ChromaError as e:
                raise ChromaDBError(f"ChromaDBへの追加に失敗: {e}")
            
            # SQLiteにメタデータを保存
            try:
                async with self.transaction() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        self.sql_statements['insert_metadata'],
                        (embedding_id, json.dumps(metadata))
                    )
            except sqlite3.Error as e:
                raise DatabaseError(f"メタデータの保存に失敗: {e}")
                
            async with self.metrics_lock:
                self.metrics.total_embeddings += 1
                self.metrics.insert_latencies.append(time.time() - start_time)
                
        except VectorStoreError:
            async with self.metrics_lock:
                self.metrics.error_count += 1
            raise
        except Exception as e:
            async with self.metrics_lock:
                self.metrics.error_count += 1
            raise VectorStoreError(f"予期せぬエラー: {e}")
            
    async def similarity_search(self, query_embedding: torch.Tensor,
                             n_results: int = 5) -> List[Dict[str, Any]]:
        """類似度検索"""
        start_time = time.time()
        try:
            # 入力値の検証
            if n_results < 1:
                raise ValueError("n_resultsは1以上である必要があります")
                
            # ChromaDBで検索
            results = self.collection.query(
                query_embeddings=query_embedding.cpu().numpy().tolist(),
                n_results=n_results
            )
            
            # メタデータの取得と変換
            similar_items = []
            for i, chroma_id in enumerate(results['ids'][0]):
                # プリペアドステートメントを使用
                async with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT metadata FROM vector_metadata WHERE chroma_id = ?", (chroma_id,))
                    row = cursor.fetchone()
                
                if row:
                    try:
                        metadata = json.loads(row[0])
                        # experienceキーが存在することを確認
                        if "experience" not in metadata:
                            metadata["experience"] = metadata.copy()
                        metadata['similarity_score'] = float(results['distances'][0][i])
                        similar_items.append(metadata)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"JSONデコードエラー: {e}")
                        continue
                        
            async with self.metrics_lock:
                self.metrics.total_queries += 1
                self.metrics.query_latencies.append(time.time() - start_time)
                
            return similar_items
            
        except sqlite3.Error as e:
            self.logger.error(f"データベースエラー: {e}")
            raise
        except Exception as e:
            self.logger.error(f"検索エラー: {e}")
            raise
            
    async def update_embedding(self, embedding_id: str,
                           new_embedding: torch.Tensor,
                           new_metadata: Dict[str, Any]) -> None:
        """埋め込みベクトルの更新"""
        try:
            # 入力値の検証
            self._validate_embedding_id(embedding_id)
            self._validate_embedding(new_embedding)
            self._validate_metadata(new_metadata)
            
            # ChromaDBの更新
            embedding_numpy = new_embedding.cpu().numpy()
            if not np.isfinite(embedding_numpy).all():
                raise ValidationError("埋め込みベクトルに無限大または非数値が含まれています")
                
            self.collection.update(
                ids=[embedding_id],
                embeddings=embedding_numpy.tolist(),
                documents=[json.dumps(new_metadata)]
            )
            
            # SQLiteの更新
            async with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    self.sql_statements['update_metadata'],
                    (json.dumps(new_metadata), embedding_id)
                )
                
        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(f"予期せぬエラー: {e}")
            
    async def delete_embedding(self, embedding_id: str) -> None:
        """埋め込みベクトルの削除"""
        try:
            # ChromaDBから削除
            self.collection.delete(ids=[embedding_id])
            
            # SQLiteから削除
            async with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM vector_metadata WHERE chroma_id = ?", (embedding_id,))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"埋め込み削除エラー: {e}")
            raise
            
    def __del__(self):
        """デストラクタ"""
        try:
            if hasattr(self, 'pool'):
                self.pool.close_all()
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")
            
    async def __aenter__(self):
        """非同期コンテキストマネージャーのエントリーポイント"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了処理"""
        self.__del__()
        
    async def get_all_metadata(self) -> List[Dict[str, Any]]:
        """全メタデータの取得"""
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata FROM vector_metadata")
            return [json.loads(row[0]) for row in cursor.fetchall()]
        
    async def clear_all(self) -> None:
        """全データの削除"""
        try:
            # ChromaDBのクリア
            self.collection.delete(ids=self.collection.get()["ids"])
            
            # SQLiteのクリア
            async with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM vector_metadata")
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"データクリアエラー: {e}")
            raise 

    async def cleanup(self):
        """リソースのクリーンアップ"""
        try:
            # 既存のクリーンアップ処理
            if hasattr(self, 'pool'):
                await self.pool.close_all()
                
            # ハードウェアモニタリングのクリーンアップ
            if hasattr(self, 'hardware_monitor'):
                self.hardware_monitor.metrics_history.clear()
                
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")
            raise VectorStoreError(f"クリーンアップに失敗: {e}")
            
    async def backup(self, backup_dir: Optional[str] = None) -> str:
        """データベースとChromaDBのバックアップを作成"""
        try:
            # バックアップディレクトリの準備
            backup_dir = Path(backup_dir) if backup_dir else self.db_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # タイムスタンプ付きのバックアップディレクトリ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"backup_{timestamp}"
            backup_path.mkdir()
            
            # データベースのバックアップ
            async with self.get_connection() as conn:
                # WALモードのチェックポイント
                conn.execute("PRAGMA wal_checkpoint(FULL)")
                
                # バックアップの作成
                backup_conn = sqlite3.connect(str(backup_path / "vector_store.db"))
                conn.backup(backup_conn)
                backup_conn.close()
                
            # ChromaDBのバックアップ
            chroma_backup_path = backup_path / "chroma"
            shutil.copytree(
                self.db_path.parent / "chroma",
                chroma_backup_path,
                dirs_exist_ok=True
            )
            
            # メタデータの保存
            metadata = {
                "timestamp": timestamp,
                "db_size": self.metrics.db_size,
                "chroma_size": self.metrics.chroma_size,
                "total_embeddings": self.metrics.total_embeddings,
                "version": "1.0"
            }
            
            with open(backup_path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
                
            self.logger.info(f"バックアップを作成しました: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"バックアップ作成エラー: {e}")
            raise VectorStoreError(f"バックアップの作成に失敗: {e}")
            
    async def restore(self, backup_path: str) -> None:
        """バックアップからの復元"""
        try:
            backup_path = Path(backup_path)
            if not backup_path.exists():
                raise ValueError(f"バックアップが見つかりません: {backup_path}")
                
            # メタデータの検証
            with open(backup_path / "metadata.json") as f:
                metadata = json.load(f)
                if metadata.get("version") != "1.0":
                    raise ValueError("互換性のないバックアップバージョン")
                    
            # 現在のデータベースをクローズ
            await self.cleanup()
            
            # データベースの復元
            shutil.copy2(
                backup_path / "vector_store.db",
                self.db_path
            )
            
            # ChromaDBの復元
            chroma_backup_path = backup_path / "chroma"
            if chroma_backup_path.exists():
                shutil.rmtree(self.db_path.parent / "chroma", ignore_errors=True)
                shutil.copytree(
                    chroma_backup_path,
                    self.db_path.parent / "chroma",
                    dirs_exist_ok=True
                )
                
            # 接続の再初期化
            self.pool = ConnectionPool(str(self.db_path))
            self.chroma_client = chromadb.Client(Settings(
                persist_directory=str(self.db_path.parent / "chroma")
            ))
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection.name
            )
            
            self.logger.info(f"バックアップから復元しました: {backup_path}")
            
        except Exception as e:
            self.logger.error(f"復元エラー: {e}")
            raise VectorStoreError(f"バックアップからの復元に失敗: {e}")
            
    async def list_backups(self, backup_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """利用可能なバックアップの一覧を取得"""
        try:
            backup_dir = Path(backup_dir) if backup_dir else self.db_path.parent / "backups"
            if not backup_dir.exists():
                return []
                
            backups = []
            for backup_path in backup_dir.glob("backup_*"):
                try:
                    with open(backup_path / "metadata.json") as f:
                        metadata = json.load(f)
                        metadata["path"] = str(backup_path)
                        backups.append(metadata)
                except Exception as e:
                    self.logger.warning(f"バックアップメタデータの読み込みエラー: {e}")
                    continue
                    
            return sorted(backups, key=lambda x: x["timestamp"], reverse=True)
            
        except Exception as e:
            self.logger.error(f"バックアップ一覧取得エラー: {e}")
            raise VectorStoreError(f"バックアップ一覧の取得に失敗: {e}")
            
    async def vacuum(self) -> None:
        """データベースの最適化"""
        try:
            async with self.get_connection() as conn:
                conn.execute("VACUUM")
                self.metrics.last_vacuum_time = datetime.now()
            self.logger.info("データベースを最適化しました")
        except Exception as e:
            self.logger.error(f"データベース最適化エラー: {e}")
            raise VectorStoreError(f"データベースの最適化に失敗: {e}")
            
    def _start_monitoring_task(self):
        """モニタリングタスクの開始"""
        async def monitoring_task():
            while True:
                try:
                    # ハードウェアメトリクスの取得
                    hw_metrics = self.hardware_monitor.get_metrics()
                    
                    # 高温時の処理
                    if hw_metrics.cpu_temp >= self.hardware_monitor.warning_temp_threshold or \
                       hw_metrics.gpu_temp >= self.hardware_monitor.warning_temp_threshold:
                        # キャッシュのクリアを検討
                        if hasattr(self, 'collection'):
                            self.collection.clear_cache()
                        
                        # 必要に応じてVACUUM実行
                        await self.vacuum()
                        
                    await asyncio.sleep(60)  # 1分間隔でモニタリング
                    
                except Exception as e:
                    self.logger.error(f"モニタリングタスクエラー: {e}")
                    await asyncio.sleep(60)
                    
        asyncio.create_task(monitoring_task())
        
    async def get_hardware_metrics(self) -> Dict[str, Any]:
        """ハードウェアメトリクスの取得"""
        metrics = self.hardware_monitor.get_metrics()
        return {
            "cpu_temperature": metrics.cpu_temp,
            "gpu_temperature": metrics.gpu_temp,
            "cpu_usage": metrics.cpu_usage,
            "gpu_usage": metrics.gpu_usage,
            "memory_usage": metrics.memory_usage,
            "timestamp": metrics.timestamp.isoformat()
        }
        
    async def get_temperature_history(self) -> Dict[str, list]:
        """温度履歴の取得"""
        return self.hardware_monitor.get_temperature_history()
        
    async def get_usage_history(self) -> Dict[str, list]:
        """使用率履歴の取得"""
        return self.hardware_monitor.get_usage_history() 