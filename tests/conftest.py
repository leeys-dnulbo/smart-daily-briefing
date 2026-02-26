"""Smart Daily Briefing - 테스트 설정"""

import os
import sys

# scripts/ 디렉토리를 Python path에 추가
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')
sys.path.insert(0, SCRIPTS_DIR)

# hooks/ 디렉토리를 Python path에 추가
HOOKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hooks')
sys.path.insert(0, HOOKS_DIR)

# 프로젝트 루트 경로
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
