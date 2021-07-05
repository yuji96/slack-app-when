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
[`ngrok`](https://ngrok.com/download)をダウンロード後に，`ngrok`を`/usr/local/bin/`に移動する．

```zsh
pipenv run server
python src/app.py
```
`ngrok`は毎回ランダムなURLを発行するので、その都度 Slack App の設定を更新しないといけない．
複数人が同時に開発しているときは，そのうちの1人が設定する．
