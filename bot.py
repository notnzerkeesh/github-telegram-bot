import os
import requests

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Загружаем переменные из файла .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

GITHUB_OWNER = "notnzerkeesh"
GITHUB_REPO = "github-telegram-bot"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я GitHub Assistant Bot.\n\n"
        "Доступные команды:\n"
        "/repo - информация о репозитории\n"
        "/commits - последние коммиты\n"
        "/issues - открытые issues\n"
        "/pulls - открытые pull requests"
    )


async def repo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

    response = requests.get(url)

    if response.status_code != 200:
        await update.message.reply_text(
            "❌ Не удалось получить информацию о репозитории."
        )
        return

    data = response.json()

    message = (
        f"📦 Repository: {data['name']}\n"
        f"👤 Owner: {data['owner']['login']}\n"
        f"⭐ Stars: {data['stargazers_count']}\n"
        f"🍴 Forks: {data['forks_count']}\n"
        f"🐛 Open issues: {data['open_issues_count']}\n\n"
        f"📝 Description: {data.get('description') or 'No description'}"
    )

    await update.message.reply_text(message)


async def commits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits"

    response = requests.get(url)

    if response.status_code != 200:
        await update.message.reply_text(
            "❌ Не удалось получить commits."
        )
        return

    commits_data = response.json()[:5]

    if not commits_data:
        await update.message.reply_text(
            "Пока нет commits."
        )
        return

    message = "📝 Последние commits:\n\n"

    for commit in commits_data:
        author = commit["commit"]["author"]["name"]
        commit_message = commit["commit"]["message"]

        message += (
            f"👤 {author}\n"
            f"💬 {commit_message}\n\n"
        )

    await update.message.reply_text(message)


async def issues(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues"

    response = requests.get(url)

    if response.status_code != 200:
        await update.message.reply_text(
            "❌ Не удалось получить issues."
        )
        return

    issues_data = response.json()[:5]

    real_issues = [
        issue for issue in issues_data
        if "pull_request" not in issue
    ]

    if not real_issues:
        await update.message.reply_text(
            "✅ Сейчас открытых issues нет."
        )
        return

    message = "🐛 Open issues:\n\n"

    for issue in real_issues:
        message += (
            f"#{issue['number']} "
            f"{issue['title']}\n"
        )

    await update.message.reply_text(message)


async def pulls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls"

    response = requests.get(url)

    if response.status_code != 200:
        await update.message.reply_text(
            "❌ Не удалось получить pull requests."
        )
        return

    pulls_data = response.json()[:5]

    if not pulls_data:
        await update.message.reply_text(
            "✅ Сейчас открытых Pull Requests нет."
        )
        return

    message = "🔀 Open Pull Requests:\n\n"

    for pull in pulls_data:
        message += (
            f"#{pull['number']} {pull['title']}\n"
            f"👤 {pull['user']['login']}\n\n"
        )

    await update.message.reply_text(message)


def main():
    if not TOKEN:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не найден в .env")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("repo", repo))
    app.add_handler(CommandHandler("commits", commits))
    app.add_handler(CommandHandler("issues", issues))
    app.add_handler(CommandHandler("pulls", pulls))

    print("✅ Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()