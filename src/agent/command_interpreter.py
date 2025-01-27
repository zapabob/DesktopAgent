import re
from typing import Dict, Any, Tuple, Optional

class CommandInterpreter:
    def __init__(self):
        self.command_patterns = {
            'BROWSER': [
                (r'ブラウザ(?:で)?(.+?)(?:を)?開いて', self._create_browser_open_command),
                (r'(.+?)(?:を)?検索して', self._create_search_command),
            ],
            'FILE': [
                (r'(.+?)フォルダ(?:を)?作成して', self._create_mkdir_command),
                (r'(.+?)(?:を)?(.+?)(?:に)?移動して', self._create_move_file_command),
                (r'(.+?)(?:を)?削除して', self._create_delete_command),
            ],
            'DESKTOP': [
                (r'(.+?)(?:を)?最小化して', self._create_minimize_command),
                (r'(.+?)(?:を)?起動して', self._create_launch_command),
            ],
            'MOUSE': [
                (r'マウスを(\d+),\s*(\d+)に移動して', self._create_mouse_move_command),
                (r'(\d+),\s*(\d+)を?(\d+)?回?(左|右|中央)?クリックして', self._create_mouse_click_command),
                (r'(\d+),\s*(\d+)から(\d+),\s*(\d+)までドラッグして', self._create_mouse_drag_command),
                (r'(上|下)に(\d+)スクロールして', self._create_mouse_scroll_command),
            ],
            'KEYBOARD': [
                (r'キー操作を記録して', self._create_keyboard_record_command),
                (r'キー操作を停止して', self._create_keyboard_stop_command),
                (r'キー操作を再生して', self._create_keyboard_replay_command),
                (r'「(.+?)」と入力して', self._create_keyboard_type_command),
                (r'ホットキー(.+?)を実行して', self._create_keyboard_hotkey_command),
            ],
            'VISION': [
                (r'画面を分析して', self._create_vision_analyze_command),
                (r'(\d+),\s*(\d+)から(\d+),\s*(\d+)の範囲を分析して', self._create_vision_region_analyze_command),
                (r'動画「(.+?)」を分析して', self._create_vision_video_analyze_command),
            ]
        }
        self.browser_commands = {
            'edge': r'^edge\s+(.+)$',
            'chrome': r'^chrome\s+(.+)$',
            'browser': r'^browser\s+(.+)$'  # デフォルトブラウザで開く
        }
    
    def interpret(self, command: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """コマンドを解釈してタイプとパラメータを返す"""
        command = command.strip().lower()
        
        # ブラウザコマンドの解釈
        for browser_type, pattern in self.browser_commands.items():
            match = re.match(pattern, command)
            if match:
                url = match.group(1)
                # URLのバリデーション
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                return 'BROWSER', {
                    'browser_type': browser_type,
                    'url': url
                }
        
        # その他のコマンドの解釈
        for command_type, patterns in self.command_patterns.items():
            for pattern, handler in patterns:
                match = re.search(pattern, command)
                if match:
                    return command_type, handler(*match.groups())
        
        return None
    
    def _create_browser_open_command(self, url: str) -> Dict[str, Any]:
        return {
            'action': 'open',
            'url': url if url.startswith('http') else f'https://{url}'
        }
    
    def _create_search_command(self, query: str) -> Dict[str, Any]:
        return {
            'action': 'search',
            'query': query
        }
    
    def _create_mkdir_command(self, path: str) -> Dict[str, Any]:
        return {
            'action': 'mkdir',
            'path': path
        }
    
    def _create_move_file_command(self, source: str, dest: str) -> Dict[str, Any]:
        return {
            'action': 'move',
            'source': source,
            'destination': dest
        }
    
    def _create_delete_command(self, path: str) -> Dict[str, Any]:
        return {
            'action': 'delete',
            'path': path
        }
    
    def _create_minimize_command(self, window: str) -> Dict[str, Any]:
        return {
            'action': 'minimize',
            'window': window
        }
    
    def _create_launch_command(self, app: str) -> Dict[str, Any]:
        return {
            'action': 'launch',
            'application': app
        }
    
    def _create_mouse_move_command(self, x: str, y: str) -> Dict[str, Any]:
        return {
            'action': 'move',
            'x': int(x),
            'y': int(y),
            'duration': 0.5
        }
    
    def _create_mouse_click_command(self, x: str, y: str, clicks: str = None, button: str = None) -> Dict[str, Any]:
        button_map = {'左': 'left', '右': 'right', '中央': 'middle'}
        return {
            'action': 'click',
            'x': int(x),
            'y': int(y),
            'clicks': int(clicks) if clicks else 1,
            'button': button_map.get(button, 'left')
        }
    
    def _create_mouse_drag_command(self, start_x: str, start_y: str, end_x: str, end_y: str) -> Dict[str, Any]:
        return {
            'action': 'drag',
            'start_x': int(start_x),
            'start_y': int(start_y),
            'end_x': int(end_x),
            'end_y': int(end_y),
            'duration': 0.5
        }
    
    def _create_mouse_scroll_command(self, direction: str, amount: str) -> Dict[str, Any]:
        scroll_amount = int(amount) * (-1 if direction == '下' else 1)
        return {
            'action': 'scroll',
            'amount': scroll_amount
        }
    
    def _create_keyboard_record_command(self) -> Dict[str, Any]:
        return {
            'action': 'record_keyboard'
        }
    
    def _create_keyboard_stop_command(self) -> Dict[str, Any]:
        return {
            'action': 'stop_keyboard'
        }
    
    def _create_keyboard_replay_command(self) -> Dict[str, Any]:
        return {
            'action': 'replay_keyboard'
        }
    
    def _create_keyboard_type_command(self, text: str) -> Dict[str, Any]:
        return {
            'action': 'type',
            'text': text
        }
    
    def _create_keyboard_hotkey_command(self, hotkey: str) -> Dict[str, Any]:
        return {
            'action': 'hotkey',
            'hotkey': hotkey
        }
    
    def _create_vision_analyze_command(self) -> Dict[str, Any]:
        return {
            'action': 'analyze_vision'
        }
    
    def _create_vision_region_analyze_command(self, start_x: str, start_y: str, end_x: str, end_y: str) -> Dict[str, Any]:
        return {
            'action': 'analyze_vision_region',
            'start_x': int(start_x),
            'start_y': int(start_y),
            'end_x': int(end_x),
            'end_y': int(end_y)
        }
    
    def _create_vision_video_analyze_command(self, video_path: str) -> Dict[str, Any]:
        return {
            'action': 'analyze_vision_video',
            'video_path': video_path
        } 