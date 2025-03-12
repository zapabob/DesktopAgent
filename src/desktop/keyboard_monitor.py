import keyboard
import logging
from typing import List, Optional, Callable
import time
from threading import Thread, Event

class KeyboardMonitor(Thread):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.recording = False
        self.key_events: List[dict] = []
        self.stop_event = Event()
        self.callback: Optional[Callable] = None
    
    def start_recording(self, callback: Optional[Callable] = None):
        """キーボード操作の記録を開始"""
        self.recording = True
        self.key_events = []
        self.callback = callback
        if not self.is_alive():
            self.start()
    
    def stop_recording(self) -> List[dict]:
        """キーボード操作の記録を停止して記録を返す"""
        self.recording = False
        return self.key_events
    
    def run(self):
        """キーボード操作の監視を実行"""
        try:
            while not self.stop_event.is_set():
                if self.recording:
                    event = keyboard.read_event()
                    if event.event_type == 'down':
                        key_event = {
                            'key': event.name,
                            'time': time.time()
                        }
                        self.key_events.append(key_event)
                        self.logger.debug(f"キー入力: {event.name}")
                        
                        if self.callback:
                            self.callback(key_event)
                time.sleep(0.01)  # CPU負荷軽減
                
        except Exception as e:
            self.logger.error(f"キーボード監視エラー: {e}")
    
    def stop(self):
        """監視を停止"""
        self.stop_event.set()
        if self.is_alive():
            self.join()
    
    def replay_events(self, events: List[dict], speed: float = 1.0):
        """記録したキーボード操作を再生"""
        try:
            if not events:
                return
            
            start_time = events[0]['time']
            for event in events:
                # 前のイベントとの時間差を計算
                wait_time = (event['time'] - start_time) / speed
                time.sleep(max(0, wait_time))
                
                # キーを押下
                keyboard.press_and_release(event['key'])
                self.logger.debug(f"キー再生: {event['key']}")
                
                start_time = event['time']
                
        except Exception as e:
            self.logger.error(f"キーボード再生エラー: {e}")
    
    def get_key_sequence(self) -> str:
        """記録したキー操作を文字列として取得"""
        return ' + '.join([event['key'] for event in self.key_events]) 