# 设置 Python 虚拟环境目录
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

# 默认目标
.PHONY: all
all: venv test

# 创建虚拟环境
.PHONY: venv
venv:
	python3 -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip
	$(PIP) install pytest pytest-cov

# 运行后端测试
.PHONY: test
test: venv
	$(PYTHON) -m pytest tests/ -v --cov=app --cov-report=term-missing

# 清理虚拟环境
.PHONY: clean
clean:
	rm -rf $(VENV_DIR)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete 