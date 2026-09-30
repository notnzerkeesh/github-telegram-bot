import os
import requests

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

DEFAULT_OWNER = "notnzerkeesh"
DEFAULT_REPO = "github-telegram-bot"


def get_repo(context):
    owner = context.user_data.get("owner", DEFAULT_OWNER)
    repo = context.user_data.get("repo", DEFAULT_REPO)
    return owner, repo


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Repository", callback_data="repo"),
            InlineKeyboardButton("📝 Commits", callback_data="commits"),
        ],
        [
            InlineKeyboardButton("🐛 Issues", callback_data="issues"),
            InlineKeyboardButton("🔀 Pull Requests", callback_data="pulls"),
        ],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner, repo = get_repo(context)

    await update.message.reply_text(
        f"👋 Привет! Я GitHub Assistant Bot.\n\n"
        f"Текущий репозиторий:\n"
        f"{owner}/{repo}\n\n"
        f"Чтобы выбрать другой репозиторий, используй:\n"
        f"/setrepo owner/repository\n\n"
        f"Например:\n"
        f"/setrepo microsoft/vscode",
        reply_markup=main_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Доступные команды:\n\n"
        "/start - главное меню\n"
        "/setrepo owner/repository - выбрать репозиторий\n"
        "/currentrepo - текущий репозиторий\n"
        "/repo - информация о репозитории\n"
        "/commits - последние коммиты\n"
        "/issues - открытые issues\n"
        "/pulls - pull requests"
    )


async def setrepo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи репозиторий.\n\n"
            "Пример:\n"
            "/setrepo microsoft/vscode"
        )
        return

    value = context.args[0].strip()

    if "/" not in value:
        await update.message.reply_text(
            "❌ Неверный формат.\n\n"
            "Используй:\n"
            "/setrepo owner/repository"
        )
        return

    owner, repo = value.split("/", 1)

    url = f"https://api.github.com/repos/{owner}/{repo}"

    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException:
        await update.message.reply_text(
            "❌ Не удалось подключиться к GitHub."
        )
        return

    if response.status_code == 404:
        await update.message.reply_text(
            "❌ Репозиторий не найден.\n"
            "Проверь owner и название repository."
        )
        return

    if response.status_code != 200:
        await update.message.reply_text(
            f"❌ GitHub вернул ошибку: {response.status_code}"
        )
        return

    context.user_data["owner"] = owner
    context.user_data["repo"] = repo

    await update.message.reply_text(
        f"✅ Репозиторий выбран:\n"
        f"{owner}/{repo}",
        reply_markup=main_keyboard(),
    )


async def currentrepo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner, repo = get_repo(context)

    await update.message.reply_text(
        f"📌 Текущий репозиторий:\n"
        f"{owner}/{repo}"
    )


async def repo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner, repo_name = get_repo(context)

    url = f"https://api.github.com/repos/{owner}/{repo_name}"

    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException:
        await update.message.reply_text(
            "❌ Ошибка подключения к GitHub."
        )
        return

    if response.status_code != 200:
        await update.message.reply_text(
            "❌ Не удалось получить информацию."
        )
        return

    data = response.json()

    message = (
        f"📦 Repository: {data['name']}\n"
        f"👤 Owner: {data['owner']['login']}\n"
        f"⭐ Stars: {data['stargazers_count']}\n"
        f"🍴 Forks: {data['forks_count']}\n"
        f"🐛 Open issues: {data['open_issues_count']}\n\n"
        f"📝 {data.get('description') or 'No description'}"
    )

    await update.message.reply_text(message)


async def commits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner, repo_name = get_repo(context)

    url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"

    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException:
        await update.message.reply_text(
            "❌ Ошибка подключения к GitHub."
        )
        return

    if response.status_code != 200:
        await update.message.reply_text(
            "❌ Не удалось получить commits."
        )
        return

    commits_data = response.json()[:5]

    if not commits_data:
        await update.message.reply_text(
            "Пока commits нет."
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
    owner, repo_name = get_repo(context)

    url = f"https://api.github.com/repos/{owner}/{repo_name}/issues"

    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException:
        await update.message.reply_text(
            "❌ Ошибка подключения к GitHub."
        )
        return

    if response.status_code != 200:
        await update.message.reply_text(
            "❌ Не удалось получить issues."
        )
        return

    issues_data = response.json()

    real_issues = [
        issue
        for issue in issues_data
        if "pull_request" not in issue
    ]

    if not real_issues:
        await update.message.reply_text(
            "✅ Сейчас открытых issues нет."
        )
        return

    message = "🐛 Open issues:\n\n"

    for issue in real_issues[:5]:
        message += (
            f"#{issue['number']} "
            f"{issue['title']}\n"
        )

    await update.message.reply_text(message)


async def pulls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner, repo_name = get_repo(context)

    url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"

    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException:
        await update.message.reply_text(
            "❌ Ошибка подключения к GitHub."
        )
        return

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
            f"#{pull['number']} "
            f"{pull['title']}\n"
            f"👤 {pull['user']['login']}\n\n"
        )

    await update.message.reply_text(message)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    owner, repo_name = get_repo(context)

    if query.data == "repo":
        url = f"https://api.github.com/repos/{owner}/{repo_name}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            await query.message.reply_text(
                "❌ Не удалось получить данные."
            )
            return

        data = response.json()

        await query.message.reply_text(
            f"📦 Repository: {data['name']}\n"
            f"👤 Owner: {data['owner']['login']}\n"
            f"⭐ Stars: {data['stargazers_count']}\n"
            f"🍴 Forks: {data['forks_count']}\n"
            f"🐛 Open issues: {data['open_issues_count']}"
        )

    elif query.data == "commits":
        url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            await query.message.reply_text(
                "❌ Не удалось получить commits."
            )
            return

        commits_data = response.json()[:5]

        if not commits_data:
            await query.message.reply_text(
                "Пока commits нет."
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

        await query.message.reply_text(message)

    elif query.data == "issues":
        url = f"https://api.github.com/repos/{owner}/{repo_name}/issues"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            await query.message.reply_text(
                "❌ Не удалось получить issues."
            )
            return

        issues_data = response.json()

        real_issues = [
            issue
            for issue in issues_data
            if "pull_request" not in issue
        ]

        if not real_issues:
            await query.message.reply_text(
                "✅ Сейчас открытых issues нет."
            )
            return

        message = "🐛 Open issues:\n\n"

        for issue in real_issues[:5]:
            message += (
                f"#{issue['number']} "
                f"{issue['title']}\n"
            )

        await query.message.reply_text(message)

    elif query.data == "pulls":
        url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            await query.message.reply_text(
                "❌ Не удалось получить Pull Requests."
            )
            return

        pulls_data = response.json()[:5]

        if not pulls_data:
            await query.message.reply_text(
                "✅ Сейчас открытых Pull Requests нет."
            )
            return

        message = "🔀 Open Pull Requests:\n\n"

        for pull in pulls_data:
            message += (
                f"#{pull['number']} "
                f"{pull['title']}\n"
                f"👤 {pull['user']['login']}\n\n"
            )

        await query.message.reply_text(message)


def main():
    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN не найден"
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("setrepo", setrepo))
    app.add_handler(CommandHandler("currentrepo", currentrepo))
    app.add_handler(CommandHandler("repo", repo))
    app.add_handler(CommandHandler("commits", commits))
    app.add_handler(CommandHandler("issues", issues))
    app.add_handler(CommandHandler("pulls", pulls))
    app.add_handler(CallbackQueryHandler(button_handler))

    port = int(os.environ.get("PORT", 10000))
    render_url = os.environ.get("RENDER_EXTERNAL_URL")

    if render_url:
        print(f"✅ Running on Render: {render_url}")

        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="telegram",
            webhook_url=f"{render_url}/telegram",
        )

    else:
        print("✅ Running locally with polling...")
        app.run_polling()


if __name__ == "__main__":
    main()