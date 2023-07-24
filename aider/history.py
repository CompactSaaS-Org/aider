import argparse
import json

import tiktoken

from aider import models, prompts
from aider.dump import dump  # noqa: F401
from aider.sendchat import simple_send_with_retries


class ChatSummary:
    def __init__(self, model=models.GPT35.name, max_tokens=1024):
        self.tokenizer = tiktoken.encoding_for_model(model)
        self.max_tokens = max_tokens

    def too_big(self, messages):
        sized = self.tokenize(messages)
        total = sum(tokens for tokens, _msg in sized)
        dump(total, self.max_tokens)
        return total > self.max_tokens

    def tokenize(self, messages):
        sized = []
        for msg in messages:
            tokens = len(self.tokenizer.encode(json.dumps(msg)))
            sized.append((tokens, msg))
        return sized

    def summarize(self, messages):
        num = len(messages)
        dump(num)
        if num < 2:
            return messages

        sized = self.tokenize(messages)
        total = sum(tokens for tokens, _msg in sized)
        if total <= self.max_tokens:
            return messages

        num = num // 2

        # we want the head to end with an assistant msg
        while messages[num]["role"] == "assistant" and num < len(messages) - 1:
            num += 1

        head = messages[:num]
        tail = messages[num:]

        summary = self.summarize_all(head)

        tail_tokens = sum(tokens for tokens, msg in sized[num:])
        summary_tokens = len(self.tokenizer.encode(json.dumps(summary)))

        result = summary + tail
        if summary_tokens + tail_tokens < self.max_tokens:
            return result

        return self.summarize(result)

    def summarize_all(self, messages):
        content = ""
        for msg in messages:
            role = msg["role"].upper()
            if role not in ("USER", "ASSISTANT"):
                continue
            content += f"# {role}\n"
            content += msg["content"]
            if not content.endswith("\n"):
                content += "\n"

        messages = [
            dict(role="system", content=prompts.summarize),
            dict(role="user", content=content),
        ]

        summary = simple_send_with_retries(model=models.GPT35.name, messages=messages)
        summary = prompts.summary_prefix + summary
        dump(summary)

        return [dict(role="user", content=summary)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="Markdown file to parse")
    args = parser.parse_args()

    with open(args.filename, "r") as f:
        text = f.read()

    messages = []
    assistant = []
    for line in text.splitlines(keepends=True):
        if line.startswith("# "):
            continue
        if line.startswith(">"):
            continue
        if line.startswith("#### /"):
            continue

        if line.startswith("#### "):
            if assistant:
                assistant = "".join(assistant)
                if assistant.strip():
                    messages.append(dict(role="assistant", content=assistant))
                assistant = []

            content = line[5:]
            if content.strip() and content.strip() != "<blank>":
                messages.append(dict(role="user", content=line[5:]))
            continue

        assistant.append(line)

    summarizer = ChatSummary(models.GPT35.name)
    summary = summarizer.summarize(messages[-40:])
    dump(summary)


if __name__ == "__main__":
    main()
