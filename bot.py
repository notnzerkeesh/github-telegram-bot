import os
import hmac
import hashlib
import json
import asyncio
import requests

from aiohttp import web
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
NOTIFY_CHAT_ID = os.getenv("TELEGRAM_NOTIFY_CHAT_ID")

DEFAULT_OWNER = "notnzerkeesh"
DEFAULT_REPO = "github-telegram-bot"

telegram_app = None


# =========================
# Repository helpers
# =========================

def get_repo(context):
    owner = context.user_data.get("owner", DEFAULT_OWNER)
    repo = context.user_data.get("repo", DEFAULT_REPO)

    return owner, repo


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📦 Repository",
                callback_data="repo",
            ),
            InlineKeyboardButton(
                "📝 Commits",
                callback_data="commits",
            ),
        ],
        [
            InlineKeyboardButton(
                "🐛 Issues",
                callback_data="issues",
            ),
            InlineKeyboardButton(
                "🔀 Pull Requests",
                callback_data="pulls",
            ),
        ],
    ])


# =========================
# Telegram commands
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    owner, repo = get_repo(context)

    await update.message.reply_text(
        f"👋 Привет! Я GitHub Assistant Bot.\n\n"
        f"📌 Текущий репозиторий:\n"
        f"{owner}/{repo}\n\n"
        f"Изменить репозиторий:\n"
        f"/setrepo owner/repository\n\n"
        f"Например:\n"
        f"/setrepo microsoft/vscode",
        reply_markup=main_keyboard(),
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "📖 Команды:\n\n"
        "/start - главное меню\n"
        "/setrepo owner/repository - выбрать repository\n"
        "/currentrepo - текущий repository\n"
        "/repo - информация\n"
        "/commits - последние commits\n"
        "/issues - issues\n"
        "/pulls - pull requests\n"
        "/chatid - показать Telegram Chat ID"
    )


async def chatid(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        f"🆔 Chat ID:\n\n{chat_id}\n\n"
        f"Этот ID можно использовать "
        f"для GitHub уведомлений."
    )


async def setrepo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи repository.\n\n"
            "Например:\n"
            "/setrepo microsoft/vscode"
        )
        return

    value = context.args[0].strip()

    if "/" not in value:
        await update.message.reply_text(
            "❌ Формат:\n"
            "/setrepo owner/repository"
        )
        return

    owner, repo = value.split("/", 1)

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo}"
    )

    try:
        response = requests.get(
            url,
            timeout=10,
        )

    except requests.RequestException:
        await update.message.reply_text(
            "❌ Ошибка подключения к GitHub."
        )
        return

    if response.status_code != 200:
        await update.message.reply_text(
            "❌ Repository не найден."
        )
        return

    context.user_data["owner"] = owner
    context.user_data["repo"] = repo

    await update.message.reply_text(
        f"✅ Repository выбран:\n"
        f"{owner}/{repo}",
        reply_markup=main_keyboard(),
    )


async def currentrepo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    owner, repo = get_repo(context)

    await update.message.reply_text(
        f"📌 Текущий repository:\n"
        f"{owner}/{repo}"
    )


async def repo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    owner, repo_name = get_repo(context)

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo_name}"
    )

    response = requests.get(
        url,
        timeout=10,
    )

    if response.status_code != 200:
        await update.message.reply_text(
            "❌ Не удалось получить repository."
        )
        return

    data = response.json()

    message = (
        f"📦 Repository: {data['name']}\n"
        f"👤 Owner: {data['owner']['login']}\n"
        f"⭐ Stars: {data['stargazers_count']}\n"
        f"🍴 Forks: {data['forks_count']}\n"
        f"🐛 Open issues: "
        f"{data['open_issues_count']}\n\n"
        f"📝 "
        f"{data.get('description') or 'No description'}"
    )

    await update.message.reply_text(message)


async def commits(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    owner, repo_name = get_repo(context)

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo_name}/commits"
    )

    response = requests.get(
        url,
        timeout=10,
    )

    if response.status_code != 200:
        await update.message.reply_text(
            "❌ Не удалось получить commits."
        )
        return

    data = response.json()[:5]

    if not data:
        await update.message.reply_text(
            "Пока commits нет."
        )
        return

    message = "📝 Последние commits:\n\n"

    for commit in data:
        author = (
            commit["commit"]
            ["author"]["name"]
        )

        commit_message = (
            commit["commit"]
            ["message"]
        )

        message += (
            f"👤 {author}\n"
            f"💬 {commit_message}\n\n"
        )

    await update.message.reply_text(
        message
    )


async def issues(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    owner, repo_name = get_repo(context)

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo_name}/issues"
    )

    response = requests.get(
        url,
        timeout=10,
    )

    if response.status_code != 200:
        await update.message.reply_text(
            "❌ Не удалось получить issues."
        )
        return

    data = response.json()

    real_issues = [
        issue
        for issue in data
        if "pull_request" not in issue
    ]

    if not real_issues:
        await update.message.reply_text(
            "✅ Открытых issues нет."
        )
        return

    message = "🐛 Open issues:\n\n"

    for issue in real_issues[:5]:
        message += (
            f"#{issue['number']} "
            f"{issue['title']}\n"
        )

    await update.message.reply_text(
        message
    )


async def pulls(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    owner, repo_name = get_repo(context)

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo_name}/pulls"
    )

    response = requests.get(
        url,
        timeout=10,
    )

    if response.status_code != 200:
        await update.message.reply_text(
            "❌ Не удалось получить PR."
        )
        return

    data = response.json()[:5]

    if not data:
        await update.message.reply_text(
            "✅ Открытых Pull Requests нет."
        )
        return

    message = "🔀 Pull Requests:\n\n"

    for pull in data:
        message += (
            f"#{pull['number']} "
            f"{pull['title']}\n"
            f"👤 {pull['user']['login']}\n\n"
        )

    await update.message.reply_text(
        message
    )


# =========================
# Buttons
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    owner, repo_name = get_repo(context)

    if query.data == "repo":

        url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repo_name}"
        )

        response = requests.get(
            url,
            timeout=10,
        )

        data = response.json()

        await query.message.reply_text(
            f"📦 {data['name']}\n"
            f"👤 {data['owner']['login']}\n"
            f"⭐ {data['stargazers_count']} stars\n"
            f"🍴 {data['forks_count']} forks"
        )

    elif query.data == "commits":

        url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repo_name}/commits"
        )

        response = requests.get(
            url,
            timeout=10,
        )

        commits_data = response.json()[:5]

        message = "📝 Последние commits:\n\n"

        for commit in commits_data:

            author = (
                commit["commit"]
                ["author"]["name"]
            )

            text = (
                commit["commit"]
                ["message"]
            )

            message += (
                f"👤 {author}\n"
                f"💬 {text}\n\n"
            )

        await query.message.reply_text(
            message
        )

    elif query.data == "issues":

        url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repo_name}/issues"
        )

        response = requests.get(
            url,
            timeout=10,
        )

        issues_data = response.json()

        real_issues = [
            issue
            for issue in issues_data
            if "pull_request" not in issue
        ]

        if not real_issues:
            await query.message.reply_text(
                "✅ Issues нет."
            )
            return

        message = "🐛 Issues:\n\n"

        for issue in real_issues[:5]:
            message += (
                f"#{issue['number']} "
                f"{issue['title']}\n"
            )

        await query.message.reply_text(
            message
        )

    elif query.data == "pulls":

        url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repo_name}/pulls"
        )

        response = requests.get(
            url,
            timeout=10,
        )

        pulls_data = response.json()[:5]

        if not pulls_data:
            await query.message.reply_text(
                "✅ Pull Requests нет."
            )
            return

        message = "🔀 Pull Requests:\n\n"

        for pull in pulls_data:
            message += (
                f"#{pull['number']} "
                f"{pull['title']}\n"
            )

        await query.message.reply_text(
            message
        )


# =========================
# GitHub webhook security
# =========================

def verify_github_signature(
    body: bytes,
    signature: str,
):

    if not GITHUB_WEBHOOK_SECRET:
        return False

    expected = (
        "sha256="
        + hmac.new(
            GITHUB_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(
        expected,
        signature,
    )


# =========================
# GitHub webhook endpoint
# =========================

async def github_webhook(request):

    body = await request.read()

    signature = request.headers.get(
        "X-Hub-Signature-256",
        "",
    )

    if not verify_github_signature(
        body,
        signature,
    ):
        return web.Response(
            status=401,
            text="Invalid signature",
        )

    event = request.headers.get(
        "X-GitHub-Event",
        "",
    )

    payload = json.loads(
        body.decode()
    )

    repository = (
        payload.get(
            "repository",
            {},
        ).get(
            "full_name",
            "Unknown repository",
        )
    )

    message = None


    # PUSH
    if event == "push":

        sender = (
            payload.get(
                "sender",
                {},
            ).get(
                "login",
                "Unknown",
            )
        )

        commits_data = payload.get(
            "commits",
            [],
        )

        branch = (
            payload.get(
                "ref",
                "",
            )
            .replace(
                "refs/heads/",
                "",
            )
        )

        message = (
            f"🚀 New Push\n\n"
            f"📦 {repository}\n"
            f"🌿 Branch: {branch}\n"
            f"👤 {sender}\n"
            f"📝 Commits: "
            f"{len(commits_data)}"
        )

        if commits_data:

            latest = commits_data[-1]

            message += (
                f"\n\n💬 "
                f"{latest.get('message')}"
            )


    # PULL REQUEST
    elif event == "pull_request":

        action = payload.get(
            "action",
        )

        pull = payload.get(
            "pull_request",
            {},
        )

        message = (
            f"🔀 Pull Request\n\n"
            f"📦 {repository}\n"
            f"⚡ Action: {action}\n"
            f"#{pull.get('number')} "
            f"{pull.get('title')}\n"
            f"👤 "
            f"{pull.get('user', {}).get('login')}"
        )


    # ISSUE
    elif event == "issues":

        action = payload.get(
            "action",
        )

        issue = payload.get(
            "issue",
            {},
        )

        message = (
            f"🐛 GitHub Issue\n\n"
            f"📦 {repository}\n"
            f"⚡ Action: {action}\n"
            f"#{issue.get('number')} "
            f"{issue.get('title')}\n"
            f"👤 "
            f"{issue.get('user', {}).get('login')}"
        )


    # PING
    elif event == "ping":

        print(
            "✅ GitHub webhook connected!"
        )

        return web.Response(
            text="pong"
        )


    if message and NOTIFY_CHAT_ID:

        await telegram_app.bot.send_message(
            chat_id=int(
                NOTIFY_CHAT_ID
            ),
            text=message,
        )


    return web.Response(
        text="OK"
    )


# =========================
# Telegram webhook endpoint
# =========================

async def telegram_webhook(request):

    data = await request.json()

    update = Update.de_json(
        data,
        telegram_app.bot,
    )

    await telegram_app.process_update(
        update
    )

    return web.Response(
        text="OK"
    )


# =========================
# Health check
# =========================

async def health(request):

    return web.Response(
        text="GitHub Telegram Bot is running 🚀"
    )


# =========================
# Startup
# =========================

async def main():

    global telegram_app

    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN not found"
        )

    telegram_app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    telegram_app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "chatid",
            chatid,
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "setrepo",
            setrepo,
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "currentrepo",
            currentrepo,
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "repo",
            repo,
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "commits",
            commits,
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "issues",
            issues,
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "pulls",
            pulls,
        )
    )

    telegram_app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    await telegram_app.initialize()

    await telegram_app.start()


    render_url = os.getenv(
        "RENDER_EXTERNAL_URL"
    )


    if render_url:

        await telegram_app.bot.set_webhook(
            url=f"{render_url}/telegram"
        )


    aio_app = web.Application()

    aio_app.router.add_post(
        "/telegram",
        telegram_webhook,
    )

    aio_app.router.add_post(
        "/github",
        github_webhook,
    )

    aio_app.router.add_get(
        "/",
        health,
    )


    runner = web.AppRunner(
        aio_app
    )

    await runner.setup()


    port = int(
        os.getenv(
            "PORT",
            10000,
        )
    )


    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port,
    )

    await site.start()


    print(
        f"✅ Server running on port {port}"
    )


    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())