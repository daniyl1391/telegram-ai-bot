"""Bilingual (Persian / English) string catalogue.

Every user-visible string in the bot lives here: buttons, messages, the admin
panel and error text. Look-ups never raise: a missing key falls back to English
and then to the key name itself, so a typo degrades gracefully instead of
crashing a handler.
"""
import logging

logger = logging.getLogger(__name__)

DEFAULT_LANG = "fa"
LANGUAGES = {"fa": "🇮🇷 فارسی", "en": "🇬🇧 English"}

STRINGS = {
    # ------------------------------------------------------------ common / menu
    "lang_choose": {
        "fa": "🌍 زبان خود را انتخاب کنید:",
        "en": "🌍 Please choose your language:",
    },
    "lang_saved": {
        "fa": "✅ زبان روی فارسی تنظیم شد.",
        "en": "✅ Language set to English.",
    },
    "welcome": {
        "fa": "👋 سلام {name}!\n\n🤖 به <b>ربات هوش مصنوعی</b> خوش آمدید.\n\n"
              "▫️ اشتراک: <b>{plan}</b>\n▫️ پیام باقی‌مانده: <b>{remaining}</b>\n\n"
              "یکی از گزینه‌ها را انتخاب کنید 👇",
        "en": "👋 Hi {name}!\n\n🤖 Welcome to the <b>AI Bot</b>.\n\n"
              "▫️ Plan: <b>{plan}</b>\n▫️ Messages left: <b>{remaining}</b>\n\n"
              "Pick an option below 👇",
    },
    "main_menu_title": {
        "fa": "🏠 <b>منوی اصلی</b>\n\nیکی از گزینه‌ها را انتخاب کنید 👇",
        "en": "🏠 <b>Main Menu</b>\n\nPick an option below 👇",
    },
    "btn_ai_chat": {"fa": "🤖 چت با هوش مصنوعی", "en": "🤖 AI Chat"},
    "btn_shop": {"fa": "🛒 فروشگاه", "en": "🛒 Shop"},
    "btn_account": {"fa": "👤 حساب من", "en": "👤 My Account"},
    "btn_support": {"fa": "🎫 پشتیبانی", "en": "🎫 Support"},
    "btn_language": {"fa": "🌍 زبان", "en": "🌍 Language"},
    "btn_back": {"fa": "◀️ بازگشت", "en": "◀️ Back"},
    "btn_main_menu": {"fa": "🏠 منوی اصلی", "en": "🏠 Main Menu"},
    "btn_cancel": {"fa": "✖️ لغو", "en": "✖️ Cancel"},
    "btn_confirm": {"fa": "✅ تایید", "en": "✅ Confirm"},
    "btn_reject": {"fa": "❌ رد", "en": "❌ Reject"},
    "btn_prev": {"fa": "⬅️", "en": "⬅️"},
    "btn_next": {"fa": "➡️", "en": "➡️"},
    "cancelled": {"fa": "✖️ لغو شد.", "en": "✖️ Cancelled."},
    "unknown_action": {
        "fa": "⚠️ این گزینه دیگر معتبر نیست. از /start شروع کنید.",
        "en": "⚠️ This option is no longer valid. Send /start to begin again.",
    },

    # ------------------------------------------------------------------ account
    "account_title": {
        "fa": "👤 <b>حساب من</b>\n\n▫️ شناسه: <code>{user_id}</code>\n"
              "▫️ اشتراک: <b>{plan}</b>\n▫️ مصرف: <b>{used}</b> از <b>{limit}</b>\n"
              "▫️ باقی‌مانده: <b>{remaining}</b>\n▫️ توکن: <b>{token_used}</b> از <b>{token_limit}</b>\n"
              "▫️ انقضا: <b>{expire}</b>",
        "en": "👤 <b>My Account</b>\n\n▫️ ID: <code>{user_id}</code>\n"
              "▫️ Plan: <b>{plan}</b>\n▫️ Used: <b>{used}</b> of <b>{limit}</b>\n"
              "▫️ Remaining: <b>{remaining}</b>\n▫️ Tokens: <b>{token_used}</b> of <b>{token_limit}</b>\n"
              "▫️ Expires: <b>{expire}</b>",
    },
    "never": {"fa": "بدون انقضا", "en": "No expiry"},
    "plan_free": {"fa": "رایگان", "en": "Free"},
    "plan_premium": {"fa": "ویژه", "en": "Premium"},

    # ------------------------------------------------------------------ ai chat
    "ai_start": {
        "fa": "🤖 <b>چت با هوش مصنوعی</b>\n\n▫️ مدل فعال: <b>{model}</b>\n"
              "▫️ پیام باقی‌مانده: <b>{remaining}</b>\n\n"
              "سوال خود را بنویسید و ارسال کنید ✍️",
        "en": "🤖 <b>AI Chat</b>\n\n▫️ Active model: <b>{model}</b>\n"
              "▫️ Messages left: <b>{remaining}</b>\n\n"
              "Type your question and send it ✍️",
    },
    "ai_thinking": {"fa": "⏳ در حال فکر کردن و نوشتن...", "en": "⏳ Thinking and writing..."},
    "ai_tokens": {"fa": "توکن", "en": "tokens"},
    "attachment_default_prompt": {
        "fa": "این فایل یا تصویر را دقیق بررسی کن و نکات مهم، اعداد و نتیجه را توضیح بده.",
        "en": "Analyze this file or image carefully and explain the key points, numbers and conclusion.",
    },
    "attachment_error": {
        "fa": "⚠️ بررسی فایل ممکن نشد.\n\n<i>{detail}</i>",
        "en": "⚠️ I could not inspect this attachment.\n\n<i>{detail}</i>",
    },
    "ai_no_models": {
        "fa": "⚠️ هنوز هیچ مدل هوش مصنوعی فعالی تنظیم نشده است. با پشتیبانی تماس بگیرید.",
        "en": "⚠️ No active AI model is configured yet. Please contact support.",
    },
    "ai_choose_model": {
        "fa": "🧠 <b>انتخاب مدل</b>\n\nمدل مورد نظر خود را انتخاب کنید:",
        "en": "🧠 <b>Choose a model</b>\n\nSelect the model you want to use:",
    },
    "btn_choose_model": {"fa": "🧠 تغییر مدل", "en": "🧠 Change model"},
    "btn_clear_history": {"fa": "🧹 پاک کردن حافظه", "en": "🧹 Clear history"},
    "ai_model_selected": {
        "fa": "✅ مدل <b>{model}</b> انتخاب شد.",
        "en": "✅ Model <b>{model}</b> selected.",
    },
    "ai_history_cleared": {
        "fa": "🧹 حافظه گفتگو پاک شد.",
        "en": "🧹 Conversation history cleared.",
    },
    "ai_failed": {
        "fa": "❌ ارتباط با سرویس هوش مصنوعی برقرار نشد. لطفاً چند لحظه بعد دوباره "
              "تلاش کنید.\n\n<i>{detail}</i>",
        "en": "❌ Could not reach the AI service. Please try again in a moment."
              "\n\n<i>{detail}</i>",
    },
    "quota_exhausted": {
        "fa": "🚫 <b>سهمیه پیام شما تمام شد.</b>\n\nبرای ادامه، یک اشتراک از "
              "فروشگاه تهیه کنید 🛒",
        "en": "🚫 <b>You have used all your messages.</b>\n\n"
              "Buy a plan from the shop to continue 🛒",
    },
    "sub_expired": {
        "fa": "⌛️ <b>اشتراک شما منقضی شده است.</b>\n\nبرای تمدید به فروشگاه بروید 🛒",
        "en": "⌛️ <b>Your subscription has expired.</b>\n\nVisit the shop to renew 🛒",
    },

    # --------------------------------------------------------------------- shop
    "shop_title": {
        "fa": "🛒 <b>فروشگاه</b>\n\nیکی از پلن‌های زیر را انتخاب کنید:",
        "en": "🛒 <b>Shop</b>\n\nChoose one of the plans below:",
    },
    "shop_empty": {
        "fa": "📭 در حال حاضر محصولی برای فروش موجود نیست.",
        "en": "📭 There are no products available right now.",
    },
    "shop_disabled": {
        "fa": "🔒 فروشگاه موقتاً غیرفعال است.",
        "en": "🔒 The shop is temporarily disabled.",
    },
    "product_detail": {
        "fa": "🛍 <b>{name}</b>\n\n{description}\n\n▫️ قیمت: <b>{price}</b> تومان\n"
              "▫️ مدت: <b>{days}</b> روز\n▫️ تعداد پیام: <b>{messages}</b>\n▫️ سهمیه: <b>{quota}</b>\n▫️ مدل‌ها: <b>{models}</b>",
        "en": "🛍 <b>{name}</b>\n\n{description}\n\n▫️ Price: <b>{price}</b>\n"
              "▫️ Duration: <b>{days}</b> days\n▫️ Messages: <b>{messages}</b>\n▫️ Quota: <b>{quota}</b>\n▫️ Models: <b>{models}</b>",
    },
    "btn_buy": {"fa": "💳 خرید", "en": "💳 Buy"},

    # ------------------------------------------------------------------ payment
    "pay_choose_method": {
        "fa": "💳 <b>روش پرداخت</b>\n\nمحصول: <b>{name}</b>\nمبلغ: <b>{price}</b> تومان",
        "en": "💳 <b>Payment method</b>\n\nProduct: <b>{name}</b>\nAmount: <b>{price}</b>",
    },
    "btn_pay_card": {"fa": "🏦 کارت به کارت", "en": "🏦 Card transfer"},
    "btn_pay_gateway": {"fa": "🌐 درگاه پرداخت", "en": "🌐 Online gateway"},
    "pay_card_instructions": {
        "fa": "🏦 <b>پرداخت کارت به کارت</b>\n\nمبلغ <b>{price}</b> تومان را به "
              "کارت زیر واریز کنید:\n\n💳 <code>{card}</code>\n👤 به نام: <b>{holder}</b>\n\n"
              "سپس <b>تصویر رسید</b> یا <b>شماره پیگیری</b> را همین‌جا ارسال کنید.\n\n"
              "🧾 شماره سفارش شما: <code>#{payment_id}</code>",
        "en": "🏦 <b>Card transfer</b>\n\nTransfer <b>{price}</b> to the card below:\n\n"
              "💳 <code>{card}</code>\n👤 Holder: <b>{holder}</b>\n\n"
              "Then send the <b>receipt photo</b> or <b>reference number</b> here.\n\n"
              "🧾 Your order number: <code>#{payment_id}</code>",
    },
    "pay_card_not_configured": {
        "fa": "⚠️ شماره کارت هنوز توسط مدیر تنظیم نشده است.",
        "en": "⚠️ The card number has not been configured by the admin yet.",
    },
    "pay_gateway_not_configured": {
        "fa": "⚠️ درگاه پرداخت فعال نیست. از کارت به کارت استفاده کنید.",
        "en": "⚠️ The online gateway is disabled. Please use card transfer.",
    },
    "pay_gateway_link": {
        "fa": "🌐 برای پرداخت روی لینک زیر بزنید:\n{url}\n\n"
              "پس از پرداخت، رسید به‌صورت خودکار بررسی می‌شود.",
        "en": "🌐 Tap the link below to pay:\n{url}\n\n"
              "Your receipt will be verified automatically after payment.",
    },
    "pay_receipt_received": {
        "fa": "✅ رسید شما دریافت شد.\n\n🧾 سفارش <code>#{payment_id}</code>\n\n"
              "پس از تایید مدیر، اشتراک شما فعال می‌شود. ممنون از صبر شما 🙏",
        "en": "✅ Your receipt has been received.\n\n🧾 Order <code>#{payment_id}</code>\n\n"
              "Your plan activates as soon as an admin approves it. Thanks for waiting 🙏",
    },
    "pay_no_pending": {
        "fa": "ℹ️ سفارش پرداخت بازی ندارید. ابتدا از فروشگاه محصولی را انتخاب کنید 🛒",
        "en": "ℹ️ You have no open payment order. Pick a product in the shop first 🛒",
    },
    "pay_approved_user": {
        "fa": "🎉 <b>پرداخت شما تایید شد!</b>\n\n▫️ پلن: <b>{plan}</b>\n"
              "▫️ تعداد پیام: <b>{messages}</b>\n▫️ اعتبار تا: <b>{expire}</b>\n\n"
              "از خرید شما متشکریم 💜",
        "en": "🎉 <b>Your payment was approved!</b>\n\n▫️ Plan: <b>{plan}</b>\n"
              "▫️ Messages: <b>{messages}</b>\n▫️ Valid until: <b>{expire}</b>\n\n"
              "Thank you for your purchase 💜",
    },
    "pay_rejected_user": {
        "fa": "❌ پرداخت سفارش <code>#{payment_id}</code> تایید نشد.\n\n"
              "در صورت اشتباه، از طریق پشتیبانی پیام بدهید 🎫",
        "en": "❌ Payment for order <code>#{payment_id}</code> was not approved.\n\n"
              "If you think this is a mistake, contact support 🎫",
    },

    # ------------------------------------------------------------------ support
    "support_title": {
        "fa": "🎫 <b>پشتیبانی</b>\n\nمشکل یا سوال خود را بنویسید تا تیکت شما ساخته "
              "شود. تیم پشتیبانی در اسرع وقت پاسخ می‌دهد.",
        "en": "🎫 <b>Support</b>\n\nDescribe your issue or question to open a ticket. "
              "Our team will reply as soon as possible.",
    },
    "support_disabled": {
        "fa": "🔒 پشتیبانی موقتاً غیرفعال است.",
        "en": "🔒 Support is temporarily disabled.",
    },
    "btn_new_ticket": {"fa": "✍️ تیکت جدید", "en": "✍️ New ticket"},
    "btn_my_tickets": {"fa": "📂 تیکت‌های من", "en": "📂 My tickets"},
    "support_ask_message": {
        "fa": "✍️ پیام خود را بنویسید و ارسال کنید:",
        "en": "✍️ Write your message and send it:",
    },
    "support_ticket_created": {
        "fa": "✅ تیکت <code>#{ticket_id}</code> ساخته شد. منتظر پاسخ باشید 🙏",
        "en": "✅ Ticket <code>#{ticket_id}</code> created. Please wait for a reply 🙏",
    },
    "support_no_tickets": {
        "fa": "📭 هنوز تیکتی نساخته‌اید.",
        "en": "📭 You have not opened any tickets yet.",
    },
    "support_ticket_view": {
        "fa": "🎫 <b>تیکت #{ticket_id}</b>\nوضعیت: <b>{status}</b>\n\n{messages}",
        "en": "🎫 <b>Ticket #{ticket_id}</b>\nStatus: <b>{status}</b>\n\n{messages}",
    },
    "support_admin_reply": {
        "fa": "📬 <b>پاسخ پشتیبانی</b> (تیکت #{ticket_id}):\n\n{message}",
        "en": "📬 <b>Support reply</b> (ticket #{ticket_id}):\n\n{message}",
    },
    "btn_reply_ticket": {"fa": "💬 پاسخ", "en": "💬 Reply"},
    "btn_close_ticket": {"fa": "🔒 بستن تیکت", "en": "🔒 Close ticket"},
    "status_open": {"fa": "باز", "en": "Open"},
    "status_answered": {"fa": "پاسخ داده شده", "en": "Answered"},
    "status_closed": {"fa": "بسته", "en": "Closed"},
    "status_pending": {"fa": "در انتظار", "en": "Pending"},
    "status_confirmed": {"fa": "تایید شده", "en": "Confirmed"},
    "status_rejected": {"fa": "رد شده", "en": "Rejected"},

    # ---------------------------------------------------------------- security
    "not_authorized": {
        "fa": "🚫 شما به این بخش دسترسی ندارید.",
        "en": "🚫 You are not authorised to use this section.",
    },
    "banned": {
        "fa": "🚫 دسترسی شما به این ربات محدود شده است.",
        "en": "🚫 Your access to this bot has been restricted.",
    },
    "rate_limited": {
        "fa": "🐢 کمی آرام‌تر! لطفاً <b>{seconds}</b> ثانیه صبر کنید.",
        "en": "🐢 Slow down! Please wait <b>{seconds}</b> seconds.",
    },
    "spam_duplicate": {
        "fa": "♻️ همین پیام را همین الان فرستادید. لطفاً پیام جدیدی بنویسید.",
        "en": "♻️ You just sent that same message. Please write something new.",
    },
    "invalid_input": {
        "fa": "⚠️ ورودی نامعتبر: {reason}\n\nدوباره تلاش کنید یا لغو کنید.",
        "en": "⚠️ Invalid input: {reason}\n\nTry again or cancel.",
    },
    "generic_error": {
        "fa": "❌ خطای غیرمنتظره‌ای رخ داد. موضوع به مدیر گزارش شد.",
        "en": "❌ An unexpected error occurred. It has been reported to the admin.",
    },
    "msg_too_long": {
        "fa": "⚠️ پیام شما بیش از حد طولانی است (حداکثر {max} کاراکتر).",
        "en": "⚠️ Your message is too long (max {max} characters).",
    },

    # ------------------------------------------------------------- admin panel
    "admin_title": {
        "fa": "👑 <b>پنل مدیریت</b>\n\n👥 کاربران: <b>{users}</b>\n"
              "🤖 مدل‌ها: <b>{models}</b>\n🛒 محصولات: <b>{products}</b>\n"
              "🧾 پرداخت‌های در انتظار: <b>{pending}</b>\n"
              "🎫 تیکت‌های باز: <b>{tickets}</b>",
        "en": "👑 <b>Admin Panel</b>\n\n👥 Users: <b>{users}</b>\n"
              "🤖 Models: <b>{models}</b>\n🛒 Products: <b>{products}</b>\n"
              "🧾 Pending payments: <b>{pending}</b>\n"
              "🎫 Open tickets: <b>{tickets}</b>",
    },
    "btn_admin_users": {"fa": "👥 کاربران", "en": "👥 Users"},
    "btn_admin_models": {"fa": "🤖 مدل‌های AI", "en": "🤖 AI Models"},
    "btn_admin_products": {"fa": "🛒 فروشگاه", "en": "🛒 Shop"},
    "btn_admin_payments": {"fa": "💳 پرداخت‌ها", "en": "💳 Payments"},
    "btn_admin_tickets": {"fa": "🎫 تیکت‌ها", "en": "🎫 Tickets"},
    "btn_admin_settings": {"fa": "⚙️ تنظیمات", "en": "⚙️ Settings"},
    "btn_admin_stats": {"fa": "📊 آمار", "en": "📊 Stats"},
    "btn_admin_broadcast": {"fa": "📢 پیام همگانی", "en": "📢 Broadcast"},
    "btn_admin_panel": {"fa": "👑 پنل مدیریت", "en": "👑 Admin panel"},

    "admin_stats_body": {
        "fa": "📊 <b>آمار</b>\n\n👥 کل کاربران: <b>{users}</b>\n"
              "🆕 کاربران امروز: <b>{users_today}</b>\n"
              "💎 اشتراک فعال: <b>{active_subs}</b>\n"
              "💬 کل پیام‌های AI: <b>{messages}</b>\n🪙 کل توکن مصرف‌شده: <b>{tokens}</b>\n"
              "💰 درآمد تاییدشده: <b>{revenue}</b> تومان\n"
              "🧾 پرداخت در انتظار: <b>{pending}</b>\n"
              "🎫 تیکت باز: <b>{tickets_open}</b>",
        "en": "📊 <b>Stats</b>\n\n👥 Total users: <b>{users}</b>\n"
              "🆕 New today: <b>{users_today}</b>\n"
              "💎 Active subscriptions: <b>{active_subs}</b>\n"
              "💬 Total AI messages: <b>{messages}</b>\n🪙 Total tokens: <b>{tokens}</b>\n"
              "💰 Confirmed revenue: <b>{revenue}</b>\n"
              "🧾 Pending payments: <b>{pending}</b>\n"
              "🎫 Open tickets: <b>{tickets_open}</b>",
    },
    "admin_users_title": {
        "fa": "👥 <b>کاربران</b> (صفحه {page} از {pages})\n\nبرای مدیریت، روی کاربر بزنید:",
        "en": "👥 <b>Users</b> (page {page} of {pages})\n\nTap a user to manage them:",
    },
    "admin_user_detail": {
        "fa": "👤 <b>{name}</b>\n\n▫️ شناسه: <code>{user_id}</code>\n"
              "▫️ نام کاربری: {username}\n▫️ زبان: {ulang}\n▫️ وضعیت: <b>{state}</b>\n"
              "▫️ عضویت: {joined}\n\n💎 اشتراک: <b>{plan}</b>\n"
              "▫️ مصرف: <b>{used}</b> از <b>{limit}</b>\n▫️ انقضا: <b>{expire}</b>",
        "en": "👤 <b>{name}</b>\n\n▫️ ID: <code>{user_id}</code>\n"
              "▫️ Username: {username}\n▫️ Language: {ulang}\n▫️ State: <b>{state}</b>\n"
              "▫️ Joined: {joined}\n\n💎 Plan: <b>{plan}</b>\n"
              "▫️ Used: <b>{used}</b> of <b>{limit}</b>\n▫️ Expires: <b>{expire}</b>",
    },
    "state_active": {"fa": "فعال", "en": "Active"},
    "state_banned": {"fa": "مسدود", "en": "Banned"},
    "btn_set_quota": {"fa": "🎚 تغییر سهمیه", "en": "🎚 Change quota"},
    "btn_set_policy": {"fa": "🧠 سیاست AI کاربر", "en": "🧠 User AI policy"},
    "admin_ask_quota_mode": {
        "fa": "🧮 حالت سهمیه را بفرستید: messages، tokens یا both",
        "en": "🧮 Send quota mode: messages, tokens or both",
    },
    "admin_ask_token_limit": {
        "fa": "🪙 سقف توکن این کاربر را به‌صورت عدد بفرستید (صفر یعنی بدون سهمیه توکن):",
        "en": "🪙 Send this user's token limit (zero disables token quota):",
    },
    "admin_ask_model_scope": {
        "fa": "🧠 مدل‌های مجاز را با نام یا ID و با کاما بفرستید؛ برای همه بنویسید all:",
        "en": "🧠 Send allowed model names/IDs separated by commas; use all for every model:",
    },
    "admin_policy_saved": {"fa": "✅ سیاست AI کاربر ذخیره شد.", "en": "✅ User AI policy saved."},
    "btn_ban": {"fa": "🚫 مسدود کردن", "en": "🚫 Ban"},
    "btn_unban": {"fa": "♻️ رفع مسدودی", "en": "♻️ Unban"},
    "btn_grant": {"fa": "🎁 اهدای اشتراک", "en": "🎁 Grant plan"},
    "btn_message_user": {"fa": "✉️ ارسال پیام", "en": "✉️ Send message"},
    "admin_user_updated": {"fa": "✅ کاربر به‌روزرسانی شد.", "en": "✅ User updated."},
    "admin_ask_quota": {
        "fa": "🎚 سهمیه پیام جدید را به‌صورت عدد بفرستید:",
        "en": "🎚 Send the new message quota as a number:",
    },
    "admin_ask_search_user": {
        "fa": "🔎 شناسه عددی یا نام کاربری را بفرستید:",
        "en": "🔎 Send a numeric ID or a username:",
    },
    "btn_search": {"fa": "🔎 جستجو", "en": "🔎 Search"},
    "admin_user_not_found": {"fa": "❔ کاربری پیدا نشد.", "en": "❔ No user found."},

    "admin_models_title": {
        "fa": "🤖 <b>مدل‌های هوش مصنوعی</b>\n\n{list}\n\nبرای ویرایش روی مدل بزنید:",
        "en": "🤖 <b>AI Models</b>\n\n{list}\n\nTap a model to edit it:",
    },
    "admin_models_empty": {
        "fa": "📭 هنوز مدلی اضافه نشده است.",
        "en": "📭 No models added yet.",
    },
    "btn_add_model": {"fa": "➕ افزودن مدل", "en": "➕ Add model"},
    "admin_model_detail": {
        "fa": "🤖 <b>{name}</b>\n\n▫️ آدرس API: <code>{api_url}</code>\n"
              "▫️ کلید API: <code>{api_key}</code>\n▫️ شناسه مدل: <code>{model_id}</code>\n"
              "▫️ وضعیت: <b>{status}</b>\n▫️ پیش‌فرض: <b>{is_default}</b>",
        "en": "🤖 <b>{name}</b>\n\n▫️ API URL: <code>{api_url}</code>\n"
              "▫️ API key: <code>{api_key}</code>\n▫️ Model ID: <code>{model_id}</code>\n"
              "▫️ Status: <b>{status}</b>\n▫️ Default: <b>{is_default}</b>",
    },
    "btn_edit_name": {"fa": "✏️ نام", "en": "✏️ Name"},
    "btn_edit_url": {"fa": "✏️ API URL", "en": "✏️ API URL"},
    "btn_edit_key": {"fa": "✏️ API KEY", "en": "✏️ API KEY"},
    "btn_edit_model_id": {"fa": "✏️ Model ID", "en": "✏️ Model ID"},
    "btn_test_model": {"fa": "🧪 تست اتصال", "en": "🧪 Test connection"},
    "btn_make_default": {"fa": "⭐️ پیش‌فرض کن", "en": "⭐️ Make default"},
    "btn_toggle_status": {"fa": "🔁 فعال/غیرفعال", "en": "🔁 Enable/Disable"},
    "btn_delete": {"fa": "🗑 حذف", "en": "🗑 Delete"},
    "on": {"fa": "روشن ✅", "en": "On ✅"},
    "off": {"fa": "خاموش ❌", "en": "Off ❌"},
    "yes": {"fa": "بله", "en": "Yes"},
    "no": {"fa": "خیر", "en": "No"},
    "admin_model_ask_name": {
        "fa": "1️⃣ یک <b>نام</b> برای مدل بفرستید (مثال: GPT-4o):",
        "en": "1️⃣ Send a <b>name</b> for the model (e.g. GPT-4o):",
    },
    "admin_model_ask_url": {
        "fa": "2️⃣ <b>آدرس API</b> را بفرستید\n(مثال: https://api.openai.com/v1/chat/completions):",
        "en": "2️⃣ Send the <b>API URL</b>\n(e.g. https://api.openai.com/v1/chat/completions):",
    },
    "admin_model_ask_key": {
        "fa": "3️⃣ <b>کلید API</b> را بفرستید:",
        "en": "3️⃣ Send the <b>API key</b>:",
    },
    "admin_model_ask_id": {
        "fa": "4️⃣ <b>شناسه مدل</b> را بفرستید (مثال: gpt-4o-mini):",
        "en": "4️⃣ Send the <b>Model ID</b> (e.g. gpt-4o-mini):",
    },
    "admin_model_saved": {
        "fa": "✅ مدل <b>{name}</b> ذخیره شد.",
        "en": "✅ Model <b>{name}</b> saved.",
    },
    "admin_model_deleted": {"fa": "🗑 مدل حذف شد.", "en": "🗑 Model deleted."},
    "admin_model_default_set": {
        "fa": "⭐️ <b>{name}</b> به‌عنوان مدل پیش‌فرض تنظیم شد.",
        "en": "⭐️ <b>{name}</b> is now the default model.",
    },
    "admin_model_test_ok": {
        "fa": "✅ <b>اتصال موفق</b>\n\nزمان پاسخ: {ms} میلی‌ثانیه\nپاسخ: <i>{sample}</i>",
        "en": "✅ <b>Connection OK</b>\n\nLatency: {ms} ms\nReply: <i>{sample}</i>",
    },
    "admin_model_test_fail": {
        "fa": "❌ <b>اتصال ناموفق</b>\n\n<code>{detail}</code>",
        "en": "❌ <b>Connection failed</b>\n\n<code>{detail}</code>",
    },
    "admin_testing": {"fa": "🧪 در حال تست...", "en": "🧪 Testing..."},

    "admin_products_title": {
        "fa": "🛒 <b>محصولات</b>\n\n{list}\n\nبرای ویرایش روی محصول بزنید:",
        "en": "🛒 <b>Products</b>\n\n{list}\n\nTap a product to edit it:",
    },
    "admin_products_empty": {
        "fa": "📭 هنوز محصولی ساخته نشده است.",
        "en": "📭 No products created yet.",
    },
    "btn_add_product": {"fa": "➕ ساخت محصول", "en": "➕ Create product"},
    "admin_product_detail": {
        "fa": "🛍 <b>{name}</b>\n\n{description}\n\n▫️ قیمت: <b>{price}</b> تومان\n"
              "▫️ مدت: <b>{days}</b> روز\n▫️ تعداد پیام: <b>{messages}</b>\n"
              "▫️ سهمیه: <b>{quota}</b>\n▫️ مدل‌ها: <b>{models}</b>\n▫️ وضعیت: <b>{status}</b>",
        "en": "🛍 <b>{name}</b>\n\n{description}\n\n▫️ Price: <b>{price}</b>\n"
              "▫️ Duration: <b>{days}</b> days\n▫️ Messages: <b>{messages}</b>\n"
              "▫️ Quota: <b>{quota}</b>\n▫️ Models: <b>{models}</b>\n▫️ Status: <b>{status}</b>",
    },
    "btn_edit_price": {"fa": "✏️ قیمت", "en": "✏️ Price"},
    "btn_edit_days": {"fa": "✏️ مدت اشتراک", "en": "✏️ Duration"},
    "btn_edit_messages": {"fa": "✏️ تعداد پیام", "en": "✏️ Messages"},
    "btn_edit_desc": {"fa": "✏️ توضیحات", "en": "✏️ Description"},
    "admin_product_ask_name": {
        "fa": "1️⃣ <b>نام</b> محصول را بفرستید:",
        "en": "1️⃣ Send the product <b>name</b>:",
    },
    "admin_product_ask_price": {
        "fa": "2️⃣ <b>قیمت</b> را به تومان و به‌صورت عدد بفرستید:",
        "en": "2️⃣ Send the <b>price</b> as a number:",
    },
    "admin_product_ask_days": {
        "fa": "3️⃣ <b>مدت اشتراک</b> را به روز بفرستید:",
        "en": "3️⃣ Send the <b>duration</b> in days:",
    },
    "admin_product_ask_messages": {
        "fa": "4️⃣ <b>تعداد پیام</b> را بفرستید:",
        "en": "4️⃣ Send the <b>message count</b>:",
    },
    "admin_product_ask_desc": {
        "fa": "5️⃣ یک <b>توضیح کوتاه</b> بفرستید (یا «-» برای خالی):",
        "en": "5️⃣ Send a short <b>description</b> (or \"-\" to skip):",
    },
    "admin_product_saved": {
        "fa": "✅ محصول <b>{name}</b> ذخیره شد.",
        "en": "✅ Product <b>{name}</b> saved.",
    },
    "admin_product_deleted": {"fa": "🗑 محصول حذف شد.", "en": "🗑 Product deleted."},

    "admin_payments_title": {
        "fa": "💳 <b>پرداخت‌ها</b>\n\n{list}",
        "en": "💳 <b>Payments</b>\n\n{list}",
    },
    "admin_payments_empty": {
        "fa": "📭 پرداخت در انتظار تاییدی وجود ندارد.",
        "en": "📭 No payments waiting for approval.",
    },
    "btn_pending_payments": {"fa": "⏳ در انتظار تایید", "en": "⏳ Pending"},
    "btn_payment_settings": {"fa": "⚙️ تنظیمات پرداخت", "en": "⚙️ Payment settings"},
    "admin_payment_detail": {
        "fa": "🧾 <b>سفارش #{payment_id}</b>\n\n▫️ کاربر: {name} (<code>{user_id}</code>)\n"
              "▫️ محصول: <b>{product}</b>\n▫️ مبلغ: <b>{amount}</b> تومان\n"
              "▫️ روش: <b>{method}</b>\n▫️ وضعیت: <b>{status}</b>\n"
              "▫️ تاریخ: {created}\n▫️ رسید: {receipt}",
        "en": "🧾 <b>Order #{payment_id}</b>\n\n▫️ User: {name} (<code>{user_id}</code>)\n"
              "▫️ Product: <b>{product}</b>\n▫️ Amount: <b>{amount}</b>\n"
              "▫️ Method: <b>{method}</b>\n▫️ Status: <b>{status}</b>\n"
              "▫️ Date: {created}\n▫️ Receipt: {receipt}",
    },
    "admin_payment_new": {
        "fa": "🔔 <b>رسید جدید</b>\n\n🧾 سفارش <code>#{payment_id}</code>\n"
              "👤 {name} (<code>{user_id}</code>)\n🛍 {product}\n💰 {amount} تومان",
        "en": "🔔 <b>New receipt</b>\n\n🧾 Order <code>#{payment_id}</code>\n"
              "👤 {name} (<code>{user_id}</code>)\n🛍 {product}\n💰 {amount}",
    },
    "admin_payment_approved": {
        "fa": "✅ سفارش #{payment_id} تایید و اشتراک فعال شد.",
        "en": "✅ Order #{payment_id} approved and the plan is now active.",
    },
    "admin_payment_rejected": {
        "fa": "❌ سفارش #{payment_id} رد شد.",
        "en": "❌ Order #{payment_id} rejected.",
    },
    "admin_ask_card": {
        "fa": "💳 شماره کارت ۱۶ رقمی را بفرستید:",
        "en": "💳 Send the 16-digit card number:",
    },
    "admin_ask_holder": {
        "fa": "👤 نام صاحب کارت را بفرستید:",
        "en": "👤 Send the card holder name:",
    },
    "btn_set_card": {"fa": "💳 شماره کارت", "en": "💳 Card number"},
    "btn_set_holder": {"fa": "👤 نام صاحب کارت", "en": "👤 Card holder"},
    "btn_toggle_gateway": {"fa": "🌐 درگاه پرداخت", "en": "🌐 Online gateway"},
    "admin_payment_settings": {
        "fa": "⚙️ <b>تنظیمات پرداخت</b>\n\n💳 کارت: <code>{card}</code>\n"
              "👤 صاحب کارت: <b>{holder}</b>\n🌐 درگاه: <b>{gateway}</b>",
        "en": "⚙️ <b>Payment settings</b>\n\n💳 Card: <code>{card}</code>\n"
              "👤 Holder: <b>{holder}</b>\n🌐 Gateway: <b>{gateway}</b>",
    },
    "not_set": {"fa": "تنظیم نشده", "en": "not set"},

    "admin_tickets_title": {
        "fa": "🎫 <b>تیکت‌ها</b>\n\n{list}",
        "en": "🎫 <b>Tickets</b>\n\n{list}",
    },
    "admin_tickets_empty": {
        "fa": "📭 تیکت بازی وجود ندارد.",
        "en": "📭 There are no open tickets.",
    },
    "admin_ask_reply": {
        "fa": "💬 پاسخ خود را برای تیکت #{ticket_id} بنویسید:",
        "en": "💬 Write your reply for ticket #{ticket_id}:",
    },
    "admin_reply_sent": {"fa": "✅ پاسخ ارسال شد.", "en": "✅ Reply sent."},
    "admin_ticket_closed": {"fa": "🔒 تیکت بسته شد.", "en": "🔒 Ticket closed."},

    "admin_settings_title": {
        "fa": "⚙️ <b>تنظیمات</b>\n\n▫️ سهمیه رایگان: <b>{free_limit}</b> پیام\n"
              "▫️ توکن رایگان: <b>{free_tokens}</b>\n▫️ حالت سهمیه: <b>{quota_mode}</b>\n"
              "▫️ دوره رایگان: <b>{free_days}</b> روز\n"
              "▫️ محدودیت نرخ: <b>{rl_msgs}</b> پیام در <b>{rl_secs}</b> ثانیه\n"
              "▫️ استریم پاسخ: <b>{streaming}</b>\n▫️ فروشگاه: <b>{shop}</b>\n▫️ پشتیبانی: <b>{support}</b>\n"
              "▫️ حافظه گفتگو: <b>{history}</b> پیام",
        "en": "⚙️ <b>Settings</b>\n\n▫️ Free quota: <b>{free_limit}</b> messages\n"
              "▫️ Free tokens: <b>{free_tokens}</b>\n▫️ Quota mode: <b>{quota_mode}</b>\n"
              "▫️ Free period: <b>{free_days}</b> days\n"
              "▫️ Rate limit: <b>{rl_msgs}</b> msgs / <b>{rl_secs}</b> s\n"
              "▫️ Streaming: <b>{streaming}</b>\n▫️ Shop: <b>{shop}</b>\n▫️ Support: <b>{support}</b>\n"
              "▫️ Chat history: <b>{history}</b> messages",
    },
    "btn_set_free_limit": {"fa": "🎚 سهمیه رایگان", "en": "🎚 Free quota"},
    "btn_set_free_tokens": {"fa": "🪙 توکن رایگان", "en": "🪙 Free tokens"},
    "btn_set_quota_mode": {"fa": "🧮 حالت سهمیه", "en": "🧮 Quota mode"},
    "btn_set_model_scope": {"fa": "🧠 مدل‌های پیش‌فرض", "en": "🧠 Default models"},
    "btn_set_stream_interval": {"fa": "⚡ سرعت نمایش", "en": "⚡ Stream speed"},
    "btn_set_output_tokens": {"fa": "🎯 سقف خروجی", "en": "🎯 Output limit"},
    "btn_set_file_size": {"fa": "📎 حجم فایل", "en": "📎 File size"},
    "btn_set_product_tokens": {"fa": "🪙 توکن پلن", "en": "🪙 Plan tokens"},
    "btn_toggle_streaming": {"fa": "✍️ پاسخ تدریجی", "en": "✍️ Streaming"},
    "quota_mode_messages": {"fa": "پیام", "en": "messages"},
    "quota_mode_tokens": {"fa": "توکن", "en": "tokens"},
    "quota_mode_both": {"fa": "پیام و توکن", "en": "messages + tokens"},
    "btn_set_free_days": {"fa": "📅 دوره رایگان", "en": "📅 Free period"},
    "btn_set_rate_limit": {"fa": "🐢 محدودیت نرخ", "en": "🐢 Rate limit"},
    "btn_toggle_shop": {"fa": "🛒 فروشگاه", "en": "🛒 Shop"},
    "btn_toggle_support": {"fa": "🎫 پشتیبانی", "en": "🎫 Support"},
    "btn_set_prompt": {"fa": "🧠 پرامپت سیستم", "en": "🧠 System prompt"},
    "btn_set_history": {"fa": "🧠 حافظه گفتگو", "en": "🧠 Chat history"},
    "admin_ask_number": {
        "fa": "🔢 مقدار جدید را به‌صورت عدد بفرستید:",
        "en": "🔢 Send the new value as a number:",
    },
    "admin_ask_text": {
        "fa": "✍️ مقدار جدید را بفرستید:",
        "en": "✍️ Send the new value:",
    },
    "admin_setting_saved": {"fa": "✅ ذخیره شد.", "en": "✅ Saved."},

    "admin_ask_broadcast": {
        "fa": "📢 پیامی که باید برای همه کاربران ارسال شود را بنویسید:",
        "en": "📢 Write the message to broadcast to all users:",
    },
    "admin_broadcast_done": {
        "fa": "📢 ارسال شد ✅ {sent} موفق / ❌ {failed} ناموفق",
        "en": "📢 Broadcast finished ✅ {sent} sent / ❌ {failed} failed",
    },
    "admin_ask_dm": {
        "fa": "✉️ پیام خود را برای این کاربر بنویسید:",
        "en": "✉️ Write your message for this user:",
    },
    "admin_dm_sent": {"fa": "✅ پیام ارسال شد.", "en": "✅ Message sent."},
    "admin_dm_failed": {
        "fa": "❌ ارسال پیام ممکن نشد (کاربر ربات را بلاک کرده است).",
        "en": "❌ Could not deliver the message (the user blocked the bot).",
    },
    "admin_notice_error": {
        "fa": "🐞 <b>خطا</b>\n<code>{where}</code>\n<code>{error}</code>",
        "en": "🐞 <b>Error</b>\n<code>{where}</code>\n<code>{error}</code>",
    },

    # -------------------------------------------------------------- validation
    "v_not_a_number": {"fa": "باید یک عدد باشد.", "en": "must be a number."},
    "v_out_of_range": {
        "fa": "باید بین {min} و {max} باشد.",
        "en": "must be between {min} and {max}.",
    },
    "v_bad_url": {
        "fa": "باید یک آدرس معتبر با http:// یا https:// باشد.",
        "en": "must be a valid URL starting with http:// or https://.",
    },
    "v_too_short": {
        "fa": "باید حداقل {min} کاراکتر باشد.",
        "en": "must be at least {min} characters.",
    },
    "v_too_long": {
        "fa": "باید حداکثر {max} کاراکتر باشد.",
        "en": "must be at most {max} characters.",
    },
    "v_bad_card": {
        "fa": "شماره کارت باید ۱۶ رقم باشد.",
        "en": "card number must be 16 digits.",
    },
    "v_bad_quota_mode": {
        "fa": "حالت سهمیه باید messages، tokens یا both باشد.",
        "en": "quota mode must be messages, tokens or both.",
    },
    "v_duplicate_name": {
        "fa": "این نام قبلاً استفاده شده است.",
        "en": "that name is already taken.",
    },
}


def normalize_lang(lang):
    return lang if lang in LANGUAGES else DEFAULT_LANG


def t(key, lang=DEFAULT_LANG, /, **kwargs):
    """Translate `key` into `lang`, formatting with kwargs. Never raises.

    `key` and `lang` are positional-only so a placeholder named "key" or "lang"
    can never collide with them (that collision was a live TypeError).
    """
    lang = normalize_lang(lang)
    entry = STRINGS.get(key)
    if entry is None:
        logger.warning("i18n: missing key %r", key)
        return key
    template = entry.get(lang) or entry.get("en") or next(iter(entry.values()))
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning("i18n: bad format for %r (%s): %s", key, lang, exc)
        return template


def missing_translations():
    """Diagnostic used by the test suite: keys not present in every language."""
    gaps = []
    for key, entry in STRINGS.items():
        for lang in LANGUAGES:
            if not entry.get(lang):
                gaps.append((key, lang))
    return gaps
