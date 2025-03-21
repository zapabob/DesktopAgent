<<<<<<< HEAD
# -*- coding: utf-8 -*-
"""Action transformer module."""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from torch.utils.data import Dataset, DataLoader

class ActionDataset(Dataset):
    """アクションデータセット"""
    def __init__(self, actions: List[Dict[str, Any]], max_length: int = 512):
        self.actions = actions
        self.max_length = max_length
        
    def __len__(self):
        return len(self.actions)
        
    def __getitem__(self, idx):
        action_data = self.actions[idx]
        encoded = self._encode_action(action_data)
        
        if len(encoded) < self.max_length:
            padding = [0] * (self.max_length - len(encoded))
            encoded.extend(padding)
        else:
            encoded = encoded[:self.max_length]
            
        return torch.tensor(encoded, dtype=torch.float32)
        
    def _encode_action(self, action_data: Dict[str, Any]) -> List[float]:
        encoded = []
        
        if 'mouse_position' in action_data:
            x, y = action_data['mouse_position']
            screen_width = action_data.get('screen_width', 1920)
            screen_height = action_data.get('screen_height', 1080)
            encoded.extend([x/screen_width, y/screen_height])
            
        button_types = ['left_click', 'right_click', 'double_click', 'drag']
        for btn in button_types:
            encoded.append(1.0 if action_data.get('button_type') == btn else 0.0)
            
        if 'timestamp' in action_data:
            time = datetime.fromisoformat(action_data['timestamp'])
            encoded.append(time.hour / 24.0)
            encoded.append(time.minute / 60.0)
            
        return encoded

class ActionTransformer(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 256,
                 num_layers: int = 4, num_heads: int = 8,
                 dropout: float = 0.1):
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        self.embedding = nn.Linear(input_dim, hidden_dim)
        self.pos_encoder = PositionalEncoding(hidden_dim, dropout)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )
        
        self.output_layer = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, input_dim)
        )
        
        self.attention_weights = None
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.embedding(x)
        x = self.pos_encoder(x)
        x = self.transformer_encoder(x)
        output = self.output_layer(x)
        return output

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 512):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) *
                           (-np.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:x.size(0)]
        return self.dropout(x)

class ActionPredictor:
    def __init__(self, input_dim: int, model_dir: Optional[str] = None,
                 device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        self.device = torch.device(device)
        self.model = ActionTransformer(input_dim).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters())
        self.criterion = nn.MSELoss()
        self.logger = logging.getLogger(__name__)
        self.model_dir = Path(model_dir) if model_dir else Path("models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = self.model_dir / "action_transformer.pth"
        if model_dir and model_path.exists():
            self.load_model(str(model_path))
        else:
            self.logger.info("事前学習済みモデルが見つかりません。新規モデルを初期化します。")
        
    async def train(self, train_loader: DataLoader,
                   num_epochs: int = 10,
                   validation_loader: Optional[DataLoader] = None):
        self.model.train()
        for epoch in range(num_epochs):
            total_loss = 0.0
            for batch in train_loader:
                batch = batch.to(self.device)
                
                self.optimizer.zero_grad()
                output = self.model(batch)
                
                loss = self.criterion(output, batch)
                total_loss += loss.item()
                
                loss.backward()
                self.optimizer.step()
                
            avg_loss = total_loss / len(train_loader)
            self.logger.info(f"Epoch {epoch+1}/{num_epochs}, Loss: {avg_loss:.4f}")
            
            if validation_loader:
                val_loss = await self.evaluate(validation_loader)
                self.logger.info(f"Validation Loss: {val_loss:.4f}")
                
            if (epoch + 1) % 5 == 0:
                self.save_model(self.model_dir / f"model_epoch_{epoch+1}.pt")
                
    async def evaluate(self, data_loader: DataLoader) -> float:
        self.model.eval()
        total_loss = 0.0
        with torch.no_grad():
            for batch in data_loader:
                batch = batch.to(self.device)
                output = self.model(batch)
                loss = self.criterion(output, batch)
                total_loss += loss.item()
        return total_loss / len(data_loader)
        
    async def predict(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        self.model.eval()
        
        dataset = ActionDataset([action_data])
        input_tensor = dataset[0].unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            output = self.model(input_tensor)
            
        predicted = output.squeeze(0).cpu().numpy()
        
        return {
            'mouse_position': (
                int(predicted[0] * action_data.get('screen_width', 1920)),
                int(predicted[1] * action_data.get('screen_height', 1080))
            ),
            'button_type': self._decode_button_type(predicted[2:6]),
            'confidence': float(torch.max(torch.softmax(torch.tensor(predicted[2:6]), dim=0)))
        }
        
    def _decode_button_type(self, button_probs: np.ndarray) -> str:
        button_types = ['left_click', 'right_click', 'double_click', 'drag']
        return button_types[np.argmax(button_probs)]
        
    def save_model(self, path: str):
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'input_dim': self.model.input_dim,
            'hidden_dim': self.model.hidden_dim
        }, path)
        
    def load_model(self, path: str):
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
=======
# -*- coding: utf-8 -*-
"""Action transformer module."""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from torch.utils.data import Dataset, DataLoader

class ActionDataset(Dataset):
    """アクションデータセット"""
    def __init__(self, actions: List[Dict[str, Any]], max_length: int = 512):
        self.actions = actions
        self.max_length = max_length
        
    def __len__(self):
        return len(self.actions)
        
    def __getitem__(self, idx):
        action_data = self.actions[idx]
        encoded = self._encode_action(action_data)
        
        if len(encoded) < self.max_length:
            padding = [0] * (self.max_length - len(encoded))
            encoded.extend(padding)
        else:
            encoded = encoded[:self.max_length]
            
        return torch.tensor(encoded, dtype=torch.float32)
        
    def _encode_action(self, action_data: Dict[str, Any]) -> List[float]:
        encoded = []
        
        if 'mouse_position' in action_data:
            x, y = action_data['mouse_position']
            screen_width = action_data.get('screen_width', 1920)
            screen_height = action_data.get('screen_height', 1080)
            encoded.extend([x/screen_width, y/screen_height])
            
        button_types = ['left_click', 'right_click', 'double_click', 'drag']
        for btn in button_types:
            encoded.append(1.0 if action_data.get('button_type') == btn else 0.0)
            
        if 'timestamp' in action_data:
            time = datetime.fromisoformat(action_data['timestamp'])
            encoded.append(time.hour / 24.0)
            encoded.append(time.minute / 60.0)
            
        return encoded

class ActionTransformer(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 256,
                 num_layers: int = 4, num_heads: int = 8,
                 dropout: float = 0.1):
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        self.embedding = nn.Linear(input_dim, hidden_dim)
        self.pos_encoder = PositionalEncoding(hidden_dim, dropout)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )
        
        self.output_layer = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, input_dim)
        )
        
        self.attention_weights = None
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.embedding(x)
        x = self.pos_encoder(x)
        x = self.transformer_encoder(x)
        output = self.output_layer(x)
        return output

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 512):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) *
                           (-np.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:x.size(0)]
        return self.dropout(x)

class ActionPredictor:
    def __init__(self, input_dim: int, model_dir: Optional[str] = None,
                 device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        self.device = torch.device(device)
        self.model = ActionTransformer(input_dim).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters())
        self.criterion = nn.MSELoss()
        self.logger = logging.getLogger(__name__)
        self.model_dir = Path(model_dir) if model_dir else Path("models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = self.model_dir / "action_transformer.pth"
        if model_dir and model_path.exists():
            self.load_model(str(model_path))
        else:
            self.logger.info("事前学習済みモデルが見つかりません。新規モデルを初期化します。")
        
    async def train(self, train_loader: DataLoader,
                   num_epochs: int = 10,
                   validation_loader: Optional[DataLoader] = None):
        self.model.train()
        for epoch in range(num_epochs):
            total_loss = 0.0
            for batch in train_loader:
                batch = batch.to(self.device)
                
                self.optimizer.zero_grad()
                output = self.model(batch)
                
                loss = self.criterion(output, batch)
                total_loss += loss.item()
                
                loss.backward()
                self.optimizer.step()
                
            avg_loss = total_loss / len(train_loader)
            self.logger.info(f"Epoch {epoch+1}/{num_epochs}, Loss: {avg_loss:.4f}")
            
            if validation_loader:
                val_loss = await self.evaluate(validation_loader)
                self.logger.info(f"Validation Loss: {val_loss:.4f}")
                
            if (epoch + 1) % 5 == 0:
                self.save_model(self.model_dir / f"model_epoch_{epoch+1}.pt")
                
    async def evaluate(self, data_loader: DataLoader) -> float:
        self.model.eval()
        total_loss = 0.0
        with torch.no_grad():
            for batch in data_loader:
                batch = batch.to(self.device)
                output = self.model(batch)
                loss = self.criterion(output, batch)
                total_loss += loss.item()
        return total_loss / len(data_loader)
        
    async def predict(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        self.model.eval()
        
        dataset = ActionDataset([action_data])
        input_tensor = dataset[0].unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            output = self.model(input_tensor)
            
        predicted = output.squeeze(0).cpu().numpy()
        
        return {
            'mouse_position': (
                int(predicted[0] * action_data.get('screen_width', 1920)),
                int(predicted[1] * action_data.get('screen_height', 1080))
            ),
            'button_type': self._decode_button_type(predicted[2:6]),
            'confidence': float(torch.max(torch.softmax(torch.tensor(predicted[2:6]), dim=0)))
        }
        
    def _decode_button_type(self, button_probs: np.ndarray) -> str:
        button_types = ['left_click', 'right_click', 'double_click', 'drag']
        return button_types[np.argmax(button_probs)]
        
    def save_model(self, path: str):
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'input_dim': self.model.input_dim,
            'hidden_dim': self.model.hidden_dim
        }, path)
        
    def load_model(self, path: str):
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict']) 