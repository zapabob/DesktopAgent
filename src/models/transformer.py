import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional, Tuple
import logging
import numpy as np

class MultiHeadAttention(nn.Module):
    """マルチヘッド自己注意機構"""
    def __init__(self, d_model: int, num_heads: int, dropout: float = 0.1):
        super().__init__()
        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        
        self.q_linear = nn.Linear(d_model, d_model)
        self.k_linear = nn.Linear(d_model, d_model)
        self.v_linear = nn.Linear(d_model, d_model)
        self.out_linear = nn.Linear(d_model, d_model)
        
        self.dropout = nn.Dropout(dropout)
        self.scale = math.sqrt(self.head_dim)
        
    def forward(self, q: torch.Tensor, k: torch.Tensor,
               v: torch.Tensor, mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        batch_size = q.size(0)
        
        # 線形変換と分割
        q = self.q_linear(q).view(batch_size, -1, self.num_heads, self.head_dim)
        k = self.k_linear(k).view(batch_size, -1, self.num_heads, self.head_dim)
        v = self.v_linear(v).view(batch_size, -1, self.num_heads, self.head_dim)
        
        # 転置してアテンション計算用に整形
        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)
        
        # アテンションスコアの計算
        scores = torch.matmul(q, k.transpose(-2, -1)) / self.scale
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float("-inf"))
            
        # アテンション重みの計算
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)
        
        # 値との積と整形
        out = torch.matmul(attn_weights, v)
        out = out.transpose(1, 2).contiguous()
        out = out.view(batch_size, -1, self.d_model)
        
        return self.out_linear(out), attn_weights

class PositionwiseFeedForward(nn.Module):
    """位置ごとのフィードフォワードネットワーク"""
    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.linear1 = nn.Linear(d_model, d_ff)
        self.linear2 = nn.Linear(d_ff, d_model)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear2(self.dropout(F.relu(self.linear1(x))))

class AgentTransformer(nn.Module):
    """エージェント用Transformerモデル"""
    def __init__(self, d_model: int, num_heads: int, num_layers: int,
                d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.d_model = d_model
        self.num_layers = num_layers
        self.logger = logging.getLogger(__name__)
        
        # エンコーダー用の埋め込み層
        self.embedding = nn.Linear(d_model, d_model)
        
        # レイヤーの構築
        self.layers = nn.ModuleList([
            nn.ModuleDict({
                'self_attn': MultiHeadAttention(d_model, num_heads, dropout),
                'feed_forward': PositionwiseFeedForward(d_model, d_ff, dropout),
                'norm1': nn.LayerNorm(d_model),
                'norm2': nn.LayerNorm(d_model)
            })
            for _ in range(num_layers)
        ])
        
        self.dropout = nn.Dropout(dropout)
        
    def encode(self, input_data: str) -> torch.Tensor:
        """入力データをベクトルに変換"""
        try:
            # 文字列をバイトに変換
            input_bytes = input_data.encode('utf-8')
            
            # バイト列を固定長のベクトルに変換
            input_array = np.frombuffer(input_bytes, dtype=np.uint8)
            if len(input_array) < self.d_model:
                # パディング
                input_array = np.pad(input_array, 
                    (0, self.d_model - len(input_array)))
            else:
                # 切り詰め
                input_array = input_array[:self.d_model]
                
            # 正規化
            input_array = input_array.astype(np.float32) / 255.0
            
            # テンソルに変換
            input_tensor = torch.from_numpy(input_array).float()
            
            # エンコード
            encoded = self.embedding(input_tensor)
            
            return encoded
            
        except Exception as e:
            self.logger.error(f"エンコードエラー: {e}")
            raise
            
    def forward(self, x: torch.Tensor,
               mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        attentions = []
        
        for layer in self.layers:
            # 自己注意機構
            residual = x
            x = layer['norm1'](x)
            x, attn = layer['self_attn'](x, x, x, mask)
            x = self.dropout(x)
            x = residual + x
            
            # フィードフォワード
            residual = x
            x = layer['norm2'](x)
            x = layer['feed_forward'](x)
            x = self.dropout(x)
            x = residual + x
            
            attentions.append(attn)
            
        return x, torch.stack(attentions)
    
    def get_attention_weights(self) -> torch.Tensor:
        """最後の自己注意の重みを取得"""
        return self.layers[-1]['self_attn'].attn_weights
    
    @staticmethod
    def create_mask(size: int) -> torch.Tensor:
        """マスクの生成"""
        mask = torch.triu(torch.ones(size, size), diagonal=1).bool()
        return ~mask
    
    def to_device(self, device: torch.device) -> 'AgentTransformer':
        """デバイスの移動"""
        return self.to(device)
    
    def save_model(self, path: str) -> None:
        """モデルの保存"""
        torch.save({
            'state_dict': self.state_dict(),
            'd_model': self.d_model,
            'num_layers': self.num_layers
        }, path)
        
    @classmethod
    def load_model(cls, path: str, device: torch.device) -> 'AgentTransformer':
        """モデルの読み込み"""
        checkpoint = torch.load(path, map_location=device)
        model = cls(
            d_model=checkpoint['d_model'],
            num_heads=8,  # デフォルト値
            num_layers=checkpoint['num_layers'],
            d_ff=checkpoint['d_model'] * 4  # デフォルト値
        )
        model.load_state_dict(checkpoint['state_dict'])
        return model.to(device) 