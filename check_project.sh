#!/bin/bash

# 🎉 СКРИПТ ПРОВЕРКИ ПРОЕКТА
# Этот скрипт проверяет, что всё правильно установлено

echo "🔍 ПРОВЕРКА ПРОЕКТА TELEGRAM TO-DO BOT"
echo "========================================"
echo ""

# 1. Проверка Python
echo "1️⃣ Проверка Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo "   ✅ Python $PYTHON_VERSION найден"
else
    echo "   ❌ Python не найден"
    exit 1
fi

echo ""

# 2. Проверка файлов проекта
echo "2️⃣ Проверка файлов проекта..."
FILES=(
    "bot.py"
    "database.py"
    "config.py"
    "requirements.txt"
    ".env.example"
    "README.md"
    "QUICK_START.md"
    "API_DOCS.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file найден"
    else
        echo "   ❌ $file НЕ найден"
    fi
done

echo ""

# 3. Проверка виртуального окружения
echo "3️⃣ Проверка виртуального окружения..."
if [ -d "venv" ]; then
    echo "   ✅ venv найден"
    
    # Проверка активации
    if [ -f "venv/bin/python" ]; then
        VENV_PYTHON="venv/bin/python"
        echo "   ✅ Python в venv доступен (Linux/Mac)"
    elif [ -f "venv/Scripts/python.exe" ]; then
        VENV_PYTHON="venv/Scripts/python.exe"
        echo "   ✅ Python в venv доступен (Windows)"
    else
        echo "   ⚠️ Python в venv не найден - может быть повреждено"
    fi
else
    echo "   ⚠️ venv не найден (создай: python3 -m venv venv)"
fi

echo ""

# 4. Проверка зависимостей
echo "4️⃣ Проверка зависимостей..."
if command -v pip3 &> /dev/null; then
    echo "   ✅ pip найден"
    
    # Проверка установленных пакетов
    echo "   📦 Установленные пакеты:"
    pip3 list 2>/dev/null | grep -E "python-telegram-bot|python-dotenv|pytz" && echo "      ✅ Основные зависимости установлены" || echo "      ❌ Некоторые зависимости отсутствуют"
else
    echo "   ❌ pip не найден"
fi

echo ""

# 5. Проверка .env файла
echo "5️⃣ Проверка .env файла..."
if [ -f ".env" ]; then
    if grep -q "TELEGRAM_BOT_TOKEN" .env; then
        TOKEN=$(grep "TELEGRAM_BOT_TOKEN" .env | cut -d '=' -f2)
        if [ "$TOKEN" != "your_bot_token_here" ] && [ -n "$TOKEN" ]; then
            echo "   ✅ .env найден с токеном"
        else
            echo "   ⚠️ .env найден, но токен не установлен"
            echo "      Добавь свой токен из @BotFather"
        fi
    fi
else
    echo "   ❌ .env не найден"
    echo "      Создай: cp .env.example .env"
fi

echo ""

# 6. Проверка синтаксиса Python файлов
echo "6️⃣ Проверка синтаксиса Python..."
for pyfile in bot.py database.py config.py; do
    if python3 -m py_compile "$pyfile" 2>/dev/null; then
        echo "   ✅ $pyfile - синтаксис OK"
    else
        echo "   ❌ $pyfile - синтаксис ошибка"
    fi
done

echo ""

# 7. Статистика документации
echo "7️⃣ Статистика документации..."
DOCS=(
    "README.md"
    "QUICK_START.md"
    "API_DOCS.md"
    "ARCHITECTURE.md"
    "ADVANCED_EXAMPLES.md"
    "RECOMMENDATIONS.md"
    "PROJECT_STRUCTURE.md"
    "INDEX.md"
    "FINAL_SUMMARY.md"
)

DOC_COUNT=0
for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        LINES=$(wc -l < "$doc")
        echo "   ✅ $doc ($LINES строк)"
        DOC_COUNT=$((DOC_COUNT + 1))
    fi
done
echo "   📊 Всего документов: $DOC_COUNT"

echo ""

# 8. Итоговая проверка
echo "========================================="
echo "✅ ПРОВЕРКА ЗАВЕРШЕНА!"
echo ""
echo "📋 РЕКОМЕНДАЦИИ:"
echo ""

if [ ! -f ".env" ] || ! grep -q "TELEGRAM_BOT_TOKEN=[^y]" .env 2>/dev/null; then
    echo "1. 🔑 Получи токен от @BotFather в Telegram"
    echo "2. 📝 Добавь токен в файл .env"
    echo ""
fi

if [ ! -d "venv" ] || [ ! -f "venv/bin/python" ]; then
    echo "1. 🐍 Создай виртуальное окружение:"
    echo "   python3 -m venv venv"
    echo "2. 🔧 Активируй его:"
    echo "   source venv/bin/activate  # Linux/Mac"
    echo "   venv\\Scripts\\activate    # Windows"
    echo ""
fi

# Проверка зависимостей
if ! python3 -c "import telegram" 2>/dev/null; then
    echo "1. 📦 Установи зависимости:"
    echo "   pip install -r requirements.txt"
    echo ""
fi

echo "3. 🚀 Запусти бота:"
echo "   python3 bot.py"
echo ""
echo "4. 💬 Открой Telegram и найди своего бота (@username)"
echo "5. 📝 Отправь команду /start"
echo ""
echo "========================================="
echo "🎉 Всё готово к запуску!"
echo ""
