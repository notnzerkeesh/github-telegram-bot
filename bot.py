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


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
DEFAULT_NOTIFY_CHAT_ID = os.getenv("TELEGRAM_NOTIFY_CHAT_ID")

DEFAULT_OWNER = "notnzerkeesh"
DEFAULT_REPO = "github-telegram-bot"

telegram_app = None


# =========================================================
# SUBSCRIBERS
# =========================================================

# Здесь хранятся Telegram chat_id пользователей,
# которые подписались на GitHub уведомления.
SUBSCRIBERS = set()

# Твой старый TELEGRAM_NOTIFY_CHAT_ID
# автоматически тоже становится подписчиком.
if DEFAULT_NOTIFY_CHAT_ID:
    try:
        SUBSCRIBERS.add(int(DEFAULT_NOTIFY_CHAT_ID))
    except ValueError:
        print("⚠️ TELEGRAM_NOTIFY_CHAT_ID должен быть числом")


# =========================================================
# HELPERS
# =========================================================

def get_repo(context):
    owner = context.user_data.get("owner", DEFAULT_OWNER)
    repo = context.user_data.get("repo", DEFAULT_REPO)

    return owner, repo


def github_get(url):
    try:
        return requests.get(
            url,
            timeout=10,
        )

    except requests.RequestException:
        return None


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

        [
            InlineKeyboardButton(
                "🔔 Subscribe",
                callback_data="subscribe",
            ),
            InlineKeyboardButton(
                "🔕 Unsubscribe",
                callback_data="unsubscribe",
            ),
        ],
    ])


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    owner, repo = get_repo(context)

    chat_id = update.effective_chat.id

    if chat_id in SUBSCRIBERS:
        status = "🔔 включены"
    else:
        status = "🔕 выключены"

    await update.message.reply_text(

        f"👋 Привет! Я GitHub Assistant Bot.\n\n"

        f"📌 Текущий репозиторий:\n"
        f"{owner}/{repo}\n\n"

        f"GitHub уведомления: {status}\n\n"

        f"Чтобы изменить repository:\n"
        f"/setrepo owner/repository\n\n"

        f"Например:\n"
        f"/setrepo microsoft/vscode",

        reply_markup=main_keyboard(),
    )


# =========================================================
# HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(

        "📖 Доступные команды:\n\n"

        "/start - главное меню\n"

        "/setrepo owner/repository - выбрать repository\n"

        "/currentrepo - текущий repository\n"

        "/repo - информация о repository\n"

        "/commits - последние commits\n"

        "/issues - открытые issues\n"

        "/pulls - pull requests\n"

        "/subscribe - включить GitHub уведомления\n"

        "/unsubscribe - отключить уведомления\n"

        "/substatus - проверить подписку\n"

        "/chatid - показать Telegram Chat ID"
    )


# =========================================================
# CHAT ID
# =========================================================

async def chatid(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    await update.message.reply_text(

        f"🆔 Chat ID:\n\n"
        f"{chat_id}"
    )


# =========================================================
# SUBSCRIBE
# =========================================================

async def subscribe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    if chat_id in SUBSCRIBERS:

        await update.message.reply_text(
            "✅ Ты уже подписан на GitHub уведомления."
        )

        return

    SUBSCRIBERS.add(chat_id)

    await update.message.reply_text(

        "🔔 Подписка включена!\n\n"

        "Теперь этот чат будет получать:\n"

        "🚀 Push notifications\n"
        "🔀 Pull Requests\n"
        "🐛 Issues\n"
        "⚙️ GitHub Actions"
    )


# =========================================================
# UNSUBSCRIBE
# =========================================================

async def unsubscribe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    if chat_id not in SUBSCRIBERS:

        await update.message.reply_text(
            "ℹ️ Уведомления уже выключены."
        )

        return

    SUBSCRIBERS.discard(chat_id)

    await update.message.reply_text(

        "🔕 GitHub уведомления отключены."
    )


# =========================================================
# SUBSCRIPTION STATUS
# =========================================================

async def substatus(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    if chat_id in SUBSCRIBERS:

        await update.message.reply_text(
            "🔔 GitHub уведомления включены."
        )

    else:

        await update.message.reply_text(
            "🔕 GitHub уведомления выключены."
        )


# =========================================================
# SET REPOSITORY
# =========================================================

async def setrepo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.args:

        await update.message.reply_text(

            "❌ Укажи repository.\n\n"

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

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo}"
    )

    response = github_get(url)

    if response is None:

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

        f"✅ Repository выбран:\n\n"

        f"{owner}/{repo}",

        reply_markup=main_keyboard(),
    )


# =========================================================
# CURRENT REPOSITORY
# =========================================================

async def currentrepo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    owner, repo = get_repo(context)

    await update.message.reply_text(

        f"📌 Текущий repository:\n\n"

        f"{owner}/{repo}"
    )


# =========================================================
# REPOSITORY INFO
# =========================================================

async def repo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    owner, repo_name = get_repo(context)

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo_name}"
    )

    response = github_get(url)

    if response is None or response.status_code != 200:

        await update.message.reply_text(

            "❌ Не удалось получить repository."
        )

        return

    data = response.json()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(

                "🔗 Open on GitHub",

                url=data["html_url"],
            )
        ]
    ])

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

    await update.message.reply_text(

        message,

        reply_markup=keyboard,
    )


# =========================================================
# COMMITS
# =========================================================

async def commits(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    owner, repo_name = get_repo(context)

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo_name}/commits"
    )

    response = github_get(url)

    if response is None or response.status_code != 200:

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

        text = (
            commit["commit"]
            ["message"]
        )

        url = commit["html_url"]

        message += (

            f"👤 {author}\n"

            f"💬 {text}\n"

            f"🔗 {url}\n\n"
        )

    await update.message.reply_text(message)


# =========================================================
# ISSUES
# =========================================================

async def issues(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    owner, repo_name = get_repo(context)

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo_name}/issues"
    )

    response = github_get(url)

    if response is None or response.status_code != 200:

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

            f"🔗 {issue['html_url']}\n\n"
        )

    await update.message.reply_text(message)


# =========================================================
# PULL REQUESTS
# =========================================================

async def pulls(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    owner, repo_name = get_repo(context)

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo_name}/pulls"
    )

    response = github_get(url)

    if response is None or response.status_code != 200:

        await update.message.reply_text(

            "❌ Не удалось получить Pull Requests."
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

            f"👤 {pull['user']['login']}\n"

            f"🔗 {pull['html_url']}\n\n"
        )

    await update.message.reply_text(message)


# =========================================================
# BUTTONS
# =========================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    chat_id = query.message.chat_id


    # SUBSCRIBE BUTTON
    if query.data == "subscribe":

        SUBSCRIBERS.add(chat_id)

        await query.message.reply_text(

            "🔔 GitHub уведомления включены!"
        )

        return


    # UNSUBSCRIBE BUTTON
    if query.data == "unsubscribe":

        SUBSCRIBERS.discard(chat_id)

        await query.message.reply_text(

            "🔕 GitHub уведомления отключены."
        )

        return


    owner, repo_name = get_repo(context)


    # REPOSITORY BUTTON
    if query.data == "repo":

        response = github_get(

            f"https://api.github.com/repos/"
            f"{owner}/{repo_name}"
        )

        if response is None or response.status_code != 200:

            await query.message.reply_text(

                "❌ Не удалось получить repository."
            )

            return

        data = response.json()

        await query.message.reply_text(

            f"📦 {data['name']}\n"

            f"👤 {data['owner']['login']}\n"

            f"⭐ {data['stargazers_count']} stars\n"

            f"🍴 {data['forks_count']} forks"
        )


    # COMMITS BUTTON
    elif query.data == "commits":

        response = github_get(

            f"https://api.github.com/repos/"
            f"{owner}/{repo_name}/commits"
        )

        if response is None or response.status_code != 200:

            await query.message.reply_text(

                "❌ Не удалось получить commits."
            )

            return

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

        await query.message.reply_text(message)


    # ISSUES BUTTON
    elif query.data == "issues":

        response = github_get(

            f"https://api.github.com/repos/"
            f"{owner}/{repo_name}/issues"
        )

        if response is None or response.status_code != 200:

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

                "✅ Issues нет."
            )

            return

        message = "🐛 Issues:\n\n"

        for issue in real_issues[:5]:

            message += (

                f"#{issue['number']} "

                f"{issue['title']}\n"
            )

        await query.message.reply_text(message)


    # PULL REQUESTS BUTTON
    elif query.data == "pulls":

        response = github_get(

            f"https://api.github.com/repos/"
            f"{owner}/{repo_name}/pulls"
        )

        if response is None or response.status_code != 200:

            await query.message.reply_text(

                "❌ Не удалось получить Pull Requests."
            )

            return

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

        await query.message.reply_text(message)


# =========================================================
# GITHUB WEBHOOK SECURITY
# =========================================================

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


# =========================================================
# SEND NOTIFICATIONS TO ALL SUBSCRIBERS
# =========================================================

async def send_notification(
    text,
    url=None,
    button_text="Open on GitHub",
):

    if not SUBSCRIBERS:

        print(
            "ℹ️ Нет подписчиков."
        )

        return


    reply_markup = None


    if url:

        reply_markup = InlineKeyboardMarkup([

            [

                InlineKeyboardButton(

                    button_text,

                    url=url,
                )

            ]

        ])


    dead_chats = []


    for chat_id in list(SUBSCRIBERS):

        try:

            await telegram_app.bot.send_message(

                chat_id=chat_id,

                text=text,

                reply_markup=reply_markup,
            )


        except Exception as error:

            print(

                f"⚠️ Ошибка отправки "
                f"{chat_id}: {error}"
            )

            dead_chats.append(chat_id)


    for chat_id in dead_chats:

        SUBSCRIBERS.discard(chat_id)


# =========================================================
# GITHUB WEBHOOK
# =========================================================

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


    # =====================================================
    # PING
    # =====================================================

    if event == "ping":

        print(

            "✅ GitHub webhook connected!"
        )

        return web.Response(

            text="pong"
        )


    # =====================================================
    # PUSH
    # =====================================================

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

            ).replace(

                "refs/heads/",

                "",
            )
        )


        compare_url = payload.get(

            "compare"
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


        await send_notification(

            message,

            compare_url,

            "Open Push on GitHub",
        )


    # =====================================================
    # PULL REQUEST
    # =====================================================

    elif event == "pull_request":

        action = payload.get(

            "action"
        )


        pull = payload.get(

            "pull_request",

            {},
        )


        merged = pull.get(

            "merged",

            False,
        )


        if action == "closed" and merged:

            title = (
                "✅ Pull Request Merged"
            )


        elif action == "opened":

            title = (
                "🔀 Pull Request Opened"
            )


        elif action == "closed":

            title = (
                "❌ Pull Request Closed"
            )


        elif action == "reopened":

            title = (
                "🔄 Pull Request Reopened"
            )


        else:

            title = (
                "🔀 Pull Request Updated"
            )


        message = (

            f"{title}\n\n"

            f"📦 {repository}\n"

            f"#{pull.get('number')} "

            f"{pull.get('title')}\n"

            f"👤 "

            f"{pull.get('user', {}).get('login')}"
        )


        await send_notification(

            message,

            pull.get(
                "html_url"
            ),

            "Open Pull Request",
        )


    # =====================================================
    # ISSUE
    # =====================================================

    elif event == "issues":

        action = payload.get(

            "action"
        )


        issue = payload.get(

            "issue",

            {},
        )


        if action == "opened":

            title = "🐛 New Issue"


        elif action == "closed":

            title = "✅ Issue Closed"


        elif action == "reopened":

            title = "🔄 Issue Reopened"


        else:

            title = "🐛 Issue Updated"


        message = (

            f"{title}\n\n"

            f"📦 {repository}\n"

            f"#{issue.get('number')} "

            f"{issue.get('title')}\n"

            f"👤 "

            f"{issue.get('user', {}).get('login')}"
        )


        await send_notification(

            message,

            issue.get(
                "html_url"
            ),

            "Open Issue",
        )


    # =====================================================
    # GITHUB ACTIONS
    # =====================================================

    elif event == "workflow_run":

        workflow_run = payload.get(

            "workflow_run",

            {},
        )


        action = payload.get(

            "action"
        )


        if action != "completed":

            return web.Response(

                text="OK"
            )


        conclusion = workflow_run.get(

            "conclusion",

            "unknown",
        )


        if conclusion == "success":

            icon = "✅"


        elif conclusion == "failure":

            icon = "❌"


        elif conclusion == "cancelled":

            icon = "⚪"


        else:

            icon = "⚙️"


        message = (

            f"{icon} GitHub Actions\n\n"

            f"📦 {repository}\n"

            f"⚙️ "
            f"{workflow_run.get('name')}\n"

            f"🌿 "
            f"{workflow_run.get('head_branch')}\n"

            f"📊 Result: "
            f"{conclusion}"
        )


        await send_notification(

            message,

            workflow_run.get(
                "html_url"
            ),

            "Open Workflow",
        )


    return web.Response(

        text="OK"
    )


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

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


# =========================================================
# HEALTH CHECK
# =========================================================

async def health(request):

    return web.Response(

        text="GitHub Telegram Bot is running 🚀"
    )


# =========================================================
# MAIN
# =========================================================

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


    # Telegram commands

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

            "subscribe",

            subscribe,
        )
    )


    telegram_app.add_handler(

        CommandHandler(

            "unsubscribe",

            unsubscribe,
        )
    )


    telegram_app.add_handler(

        CommandHandler(

            "substatus",

            substatus,
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


    # =====================================================
    # TELEGRAM WEBHOOK
    # =====================================================

    render_url = os.getenv(

        "RENDER_EXTERNAL_URL"
    )


    if render_url:

        await telegram_app.bot.set_webhook(

            url=(
                f"{render_url}/telegram"
            )
        )


    # =====================================================
    # WEB SERVER
    # =====================================================

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


    print(

        f"🔔 Subscribers: "
        f"{len(SUBSCRIBERS)}"
    )


    await asyncio.Event().wait()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    asyncio.run(main())