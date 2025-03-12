# -*- coding: utf-8 -*-
"""Agent manager module."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import torch
from ..models.action_transformer import ActionPredictor
from ..monitoring.hardware_monitor import HardwareMonitor

class ChildAgent:
    """子エージェントクラス"""
    def __init__(self, agent_id: str, role: str):
        self.agent_id = agent_id
        self.role = role
        self.status = "initialized"
        self.current_task = None
        self.last_action = None
        self.performance_metrics = {}
        
    async def execute_task(self, task: Dict):
        """タスクの実行"""
        self.status = "running"
        self.current_task = task
        try:
            # タスク実行のロジック
            result = await self._process_task(task)
            self.status = "completed"
            return result
        except Exception as e:
            self.status = "error"
            raise e
            
    async def _process_task(self, task: Dict) -> Dict:
        """タスク処理の実装"""
        # 具体的なタスク処理ロジックをここに実装
        pass

class AutonomousAgentManager:
    """自律エージェントマネージャー"""
    def __init__(self, config, db_manager):
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.child_agents = {}
        self.action_predictor = ActionPredictor(
            input_dim=8,  # マウス位置(2) + ボタン種類(4) + 時間情報(2)
            model_dir="models"
        )
        self.hardware_monitor = HardwareMonitor()
        self.running = False
        
    async def start(self):
        """エージェントマネージャーの開始"""
        self.running = True
        self.logger.info("エージェントマネージャーを開始します")
        
        # 子エージェントの初期化
        await self._initialize_child_agents()
        
        # メインループの開始
        asyncio.create_task(self._main_loop())
        
    async def stop(self):
        """エージェントマネージャーの停止"""
        self.running = False
        self.logger.info("エージェントマネージャーを停止します")
        
    async def _initialize_child_agents(self):
        """子エージェントの初期化"""
        try:
            agent_configs = self.config.get('agents', [])
            if not agent_configs:
                self.logger.warning("エージェント設定が見つかりません。デフォルト設定を使用します。")
                agent_configs = [{
                    'id': 'default_agent',
                    'role': 'general_worker',
                    'type': 'worker',
                    'priority': 1
                }]
                
            for config in agent_configs:
                try:
                    if 'id' not in config or 'role' not in config:
                        self.logger.error(f"無効なエージェント設定: {config}")
                        continue
                        
                    # 既存のエージェントをスキップ
                    if config['id'] in self.child_agents:
                        continue
                        
                    agent = ChildAgent(
                        agent_id=config['id'],
                        role=config['role']
                    )
                    
                    # 追加の設定の適用
                    agent.type = config.get('type', 'worker')
                    agent.priority = config.get('priority', 1)
                    agent.capabilities = config.get('capabilities', [])
                    
                    # モデル設定の適用（存在する場合）
                    if 'model' in config:
                        agent.model = config['model']
                        agent.max_tokens = config.get('max_tokens', 1000)
                        agent.temperature = config.get('temperature', 0.7)
                        
                    self.child_agents[config['id']] = agent
                    self.logger.info(
                        f"子エージェントを初期化: {config['id']} "
                        f"(役割: {config['role']}, タイプ: {agent.type})"
                    )
                    
                except Exception as e:
                    self.logger.error(f"エージェント {config.get('id', 'unknown')} の初期化エラー: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"子エージェントの初期化エラー: {e}")
            raise
        
    async def _main_loop(self):
        """メインループ"""
        while self.running:
            try:
                # ハードウェアメトリクスの取得
                metrics = self.hardware_monitor.get_metrics()
                
                # リソース使用状況の確認
                if self._should_optimize_resources(metrics):
                    await self._optimize_resource_usage()
                    
                # 子エージェントの状態確認と必要に応じたタスク割り当て
                await self._manage_child_agents()
                
                # 短い待機時間
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"メインループエラー: {e}")
                await asyncio.sleep(5)
                
    def _should_optimize_resources(self, metrics: Dict[str, Any]) -> bool:
        """リソース最適化の必要性を判断"""
        try:
            cpu_threshold = self.config.get('system_settings', {}).get('cpu_threshold', 80)
            memory_threshold = self.config.get('system_settings', {}).get('memory_threshold', 85)
            
            return (
                metrics.get('cpu_usage', 0) > cpu_threshold or
                metrics.get('memory_usage', 0) > memory_threshold or
                metrics.get('gpu_memory_usage', 0) > 90  # GPUメモリ使用率の閾値
            )
        except Exception as e:
            self.logger.error(f"リソース最適化チェックエラー: {e}")
            return False
                
    async def _optimize_resource_usage(self):
        """リソース使用の最適化"""
        # 高負荷の子エージェントの特定と最適化
        for agent in self.child_agents.values():
            if agent.status == "running" and self._is_high_resource_usage(agent):
                await self._pause_agent(agent.agent_id)
                
    async def _manage_child_agents(self):
        """子エージェントの管理"""
        for agent_id, agent in self.child_agents.items():
            try:
                if agent.status == "error":
                    await self._restart_agent(agent_id)
                elif agent.status == "idle":
                    await self._assign_task(agent_id)
            except Exception as e:
                self.logger.error(f"エージェント管理エラー: {agent_id}, {e}")
                
    async def predict_next_action(self, current_state: Dict) -> Dict:
        """次のアクションを予測"""
        try:
            return await self.action_predictor.predict(current_state)
        except Exception as e:
            self.logger.error(f"アクション予測エラー: {e}")
            return None
            
    async def train_action_model(self, training_data: List[Dict]):
        """アクションモデルの学習"""
        try:
            # データローダーの作成
            from torch.utils.data import DataLoader
            from ..models.action_transformer import ActionDataset
            
            dataset = ActionDataset(training_data)
            train_loader = DataLoader(
                dataset,
                batch_size=32,
                shuffle=True
            )
            
            # モデルの学習
            await self.action_predictor.train(
                train_loader,
                num_epochs=10
            )
            
            self.logger.info("アクションモデルの学習が完了しました")
            
        except Exception as e:
            self.logger.error(f"モデル学習エラー: {e}")
            
    async def _restart_agent(self, agent_id: str):
        """エージェントの再起動"""
        agent = self.child_agents.get(agent_id)
        if agent:
            agent.status = "initialized"
            self.logger.info(f"エージェントを再起動: {agent_id}")
            
    async def _pause_agent(self, agent_id: str):
        """エージェントの一時停止"""
        agent = self.child_agents.get(agent_id)
        if agent:
            agent.status = "paused"
            self.logger.info(f"エージェントを一時停止: {agent_id}")
            
    async def _assign_task(self, agent_id: str):
        """タスクの割り当て"""
        agent = self.child_agents.get(agent_id)
        if agent:
            # タスク割り当てのロジックを実装
            pass
            
    def _is_high_resource_usage(self, agent: ChildAgent) -> bool:
        """エージェントのリソース使用状況を確認"""
        try:
            metrics = agent.performance_metrics
            return (
                metrics.get('cpu_usage', 0) > 80 or
                metrics.get('memory_usage', 0) > 85 or
                metrics.get('gpu_usage', 0) > 90
            )
        except Exception as e:
            self.logger.error(f"リソース使用状況チェックエラー: {e}")
            return False

    async def log_action(self, agent_id: str, action: str, metadata: Dict[str, Any]):
        """エージェントアクションのログ記録"""
        try:
            self.db_manager.log_agent_action(agent_id, action, metadata)
            self.logger.info(f"アクションをログに記録: {agent_id}, {action}")
        except Exception as e:
            self.logger.error(f"ログ記録エラー: {e}")
        
    async def save_metrics(self, model_name: str, response_time: float,
                         success_rate: float, cost: float):
        """AIモデルメトリクスの保存"""
        self.db_manager.save_model_metrics(
            model_name, response_time, success_rate, cost
        ) 