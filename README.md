# OpenAI chatbot with memory

OpenAIのAPIを利用したチャットボットの雛形です。sqlite3を利用して、過去の会話ログの記憶を可能としています。

## 実行方法

### 共有ライブラリのビルド
まず、`native/vector_cosine_similarity.c` を共有ライブラリとしてビルドします。

#### For MacOS

以下のコマンドを実行して、`vector_cosine_similarity.dylib` を生成します。

> **Warning**
> `gcc` は `clang` のエイリアスではなく、本物の `gcc` を利用してください。
>
> Homebrew経由でインストールした場合は `gcc-11` や　`gcc-12` のような名前のコマンドになっています。

```bash
curl -L "https://www.sqlite.org/src/tarball/sqlite.tar.gz?r=release" --output sqlite3.tgz
tar xvf sqlite3.tgz
cd ./sqlite
./configure
make -j2
sudo cp ./sqlite3 /usr/local/bin/sqlite3
cd ..
gcc -dynamiclib \
    -o openai_secretary/plugins/vector_cosine_similarity.dylib \
    ./native/vector_cosine_similarity.c \
    -lm -lsqlite3 -I./sqlite -L./sqlite
```

#### For Linux

MacOSと同様のコマンドで `vector_cosine_similarity.so` を生成します。

```bash
curl -L https://www.sqlite.org/src/tarball/sqlite.tar.gz?r=release --output sqlite3.tgz
tar xvf sqlite3.tgz
cd ./sqlite
./configure
make -j2
sudo ./libtool --mode=install install -c libsqlite3.la /usr/local/lib/
sudo cp ./sqlite3 /usr/local/bin/sqlite3
cd ..
gcc -shared -fPIC \
    -o openai_secretary/plugins/vector_cosine_similarity.so \
    ./native/vector_cosine_similarity.c \
    -lm -lsqlite3 -I./sqlite -L./sqlite
```

### 依存関係のインストール

次に、依存関係をインストールします。

```bash
poetry install
```

### 環境変数の設定

`pyproject.toml` と同階層に、 `.secret` ファイルを作成します。このファイルの中には、OpenAIのAPIキーを記述します。

```bash
echo "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" > .secret
```

### 実行

ここまで完了したら、以下のコマンドで実行します。

```bash
poetry run python -m openai_secretary
```

## プロンプトのカスタマイズ

`openai_secretary/resource/resource.py` の `initial_messages` を編集することで、初期のプロンプトの内容を変更できます。
また、同じファイル内の `create_initial_context` 関数を編集すると、起動時に読み込まれるプロンプトの内容を変更できます。
