<!-- Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). -->
# Start a whole project

A task is one small change. A **project** is the whole thing: you say what you want built, vibey
interviews you about it, writes the design, builds it, and reviews it, stopping only for the
decisions that are yours.

**krypton: Start a new project** (or `@krypton /new greeter a web page that greets the visitor by
name`) creates it in the folder you have open and starts its worker.

Then just talk to it in the chat:

- `@krypton /next` shows the oldest question it is waiting on, with the answers numbered.
- `@krypton /reply 1` answers it. You can also say the answer in words.
- `@krypton /status` shows which phase it is in.
- `@krypton /pause` stops the work (nothing is lost), and `/resume` starts it again.
- `@krypton /unwind` ends a project for good. It shows what would be cancelled first and asks you to
  confirm; the reason you give is recorded on its ledger.

Nothing is built outside your folder, and nothing is spent past the caps you set under **Budgets**.
