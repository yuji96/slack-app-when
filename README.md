# Manager-to-Participants

## setup (for Mac)
```zsh
$ pip install pipenv
$ pipenv sync --dev
```
### vscode の設定
1. pipenvのpythonのパスを取得する．
```zsh
$ pipenv shell
$ which python
~/.local/share/virtualenvs/<your-python-path>/bin/python
```
2. `setting.json`にパスを追加する．

```json
"python.pythonPath": "~/.local/share/virtualenvs/<your-python-path>/bin/python",
```

## run
```zsh
pipenv run server
python src/app.py
```
