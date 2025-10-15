import random
from collections import defaultdict, Counter
from pathlib import Path
import time
from fugashi import Tagger  # ← MeCab の代わりにこちら

# ===== 設定 =====
N = 5  # n-gram の n（3〜4あたりが無難）
MAX_LEN = 1000  # 1文の最大トークン数
END_TOKENS = {"。", "！", "？", "\n"}  # 終端トークン
START_EXCLUDE = {"が", "に", "で", "から", "を", "は", "て", "と", "も", "へ", "や", "の", "より", "しか","だけ","だり"}  # 文頭にしないトークン

tagger = Tagger()  # デフォルトで分かち書き相当


def is_particle(word: str) -> bool:
    for token in tagger(word):
        # feature がオブジェクトの場合、 .pos で品詞のタプルが取れる
        # 例: ('助詞', '格助詞', '一般', '*')
        pos = getattr(token.feature, "pos", None)
        if pos and len(pos) > 0 and pos[0] == "助詞":
            return True
        # 古いMeCab辞書なら feature が文字列の可能性もあるのでフォールバック
        if isinstance(token.feature, str) and token.feature.split(',')[0] == "助詞":
            return True
    return False

# ===== 関数群 =====
def tokenize(text: str):
    """fugashiで分かち書き→トークン配列を返す"""
    return [word.surface for word in tagger(text)]

def load_corpus(paths):
    texts = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for f in p.glob("**/*.txt"):
                texts.append(f.read_text(encoding="utf-8", errors="ignore"))
        else:
            texts.append(p.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(texts)

def build_model(text, n=N):
    """トークン単位でマルコフモデル構築"""
    tokens = tokenize(text)
    model = defaultdict(Counter)
    if len(tokens) < n:
        return model
    for i in range(len(tokens) - n):
        state = tuple(tokens[i:i + n - 1])
        nxt = tokens[i + n - 1]
        model[state][nxt] += 1
    return model

def choose_next(counter):
    tokens, weights = zip(*counter.items())
    return random.choices(tokens, weights=weights, k=1)[0]

def generate_sentence(model, n=N, max_len=MAX_LEN, seed=None):
    if seed is not None:
        random.seed(seed)
    if not model:
        return ""

    candidates = [s for s in model.keys() if s[0] not in END_TOKENS]
    if not candidates:
        candidates = list(model.keys())

    while True:
        state = random.choice(candidates)
        # fugashiで助詞チェック
        if not is_particle(state[0]):
            break

    out = list(state)

    while len(out) < max_len:
        counter = model.get(state)
        if not counter:
            break
        nxt = choose_next(counter)
        out.append(nxt)
        if nxt in END_TOKENS:
            break
        state = tuple(out[-(n - 1):])

    return "".join(out)

def endless_stream(model, n=N, seed=None, delay=0.05):
    i = 0
    while True:
        s = generate_sentence(model, n=n, seed=None if seed is None else seed + i)
        if s.strip():
            for ch in s:
                print(ch, end='', flush=True)
                time.sleep(delay)
            print()
        i += 1

def slow_print(text, delay=0.1):
    for ch in text:
        print(ch, end='', flush=True)
        time.sleep(delay)

# ===== 実行部 =====
if __name__ == "__main__":
    corpus = load_corpus(["./novels"])
    model = build_model(corpus, n=N)
    ask_mode = input("エンドレスモードで出力しますか？ (y/n): ").strip().lower() == 'y'
    if ask_mode:
        ask_seed = input("シード値を指定しますか？ (y/n): ").strip().lower() == 'y'
        if ask_seed:
            seed_input = input("シード値を入力してください: ").strip()
            try:
                seed_value = int(seed_input)
            except ValueError:
                seed_value = sum(ord(c) for c in seed_input)
            print(f"→ シード値（変換後）: {seed_value}")
            endless_stream(model, n=N, seed=seed_value)
        else:
            endless_stream(model, n=N)
    else:
        while True:
            ask_for = input("何回出力しますか？ (数字を入力): ").strip()
            try:
                count = int(ask_for)
                for _ in range(count):
                    sentence = generate_sentence(model, n=N)
                    slow_print(sentence, delay=0.05)
                    print()
            except ValueError:
                count = 1
                sentence = generate_sentence(model, n=N)
                slow_print(sentence, delay=0.05)
            print()
            cont = input("終了しますか？(y/n): ").strip().lower()
            if cont == 'y':
                break