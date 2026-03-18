import sqlite3
import nest_asyncio
import telegram

from telegram.ext import Application, CommandHandler, MessageHandler, filters

BOT_TOKEN = '8317054228:AAGmys1qIwYtq5pyCyYUK7qcY49LbVF01CQ'

application = Application.builder().token(BOT_TOKEN).build()
print("Telegram bot Application instance re-created.")

def init_db():
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL UNIQUE,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    print("Database 'players.db' initialized and 'players' table ensured.")

init_db()

def predict_winner(player1_wins, player1_losses, player2_wins, player2_losses):
    player1_total_games = player1_wins + player1_losses
    player2_total_games = player2_wins + player2_losses

    player1_win_rate = player1_wins / player1_total_games if player1_total_games > 0 else 0
    player2_win_rate = player2_wins / player2_total_games if player2_total_games > 0 else 0

    if player1_win_rate > player2_win_rate:
        return f"{player1_wins} (with a higher win rate)"
    elif player2_win_rate > player1_win_rate:
        return f"{player2_wins} (with a higher win rate)"
    else:
        return "It's a tie or an uncertain outcome (win rates are equal or no games played by either)."

async def start(update, context):
    await update.message.reply_text('Hi! I am your 1v1 match prediction bot. Send /command_list to see all available commands.')
    print("Start command handler defined with updated message.")

async def add_player(update, context):
    args = context.args
    if not args or len(args) > 3:
        await update.message.reply_text('Usage: /add_player <nickname> [wins] [losses]')
        return

    nickname = args[0]
    wins = 0
    losses = 0

    if len(args) > 1:
        try:
            wins = int(args[1])
            if wins < 0:
                await update.message.reply_text('Wins must be a non-negative number.')
                return
        except ValueError:
            await update.message.reply_text('Wins must be an integer.')
            return
    if len(args) > 2:
        try:
            losses = int(args[2])
            if losses < 0:
                await update.message.reply_text('Losses must be a non-negative number.')
                return
        except ValueError:
            await update.message.reply_text('Losses must be an integer.')
            return

    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO players (nickname, wins, losses) VALUES (?, ?, ?)", (nickname, wins, losses))
        conn.commit()
        await update.message.reply_text(f'Player {nickname} added successfully with Wins: {wins}, Losses: {losses}!')
        print(f"Player {nickname} added with Wins: {wins}, Losses: {losses}.")
    except sqlite3.IntegrityError:
        await update.message.reply_text(f'Player {nickname} already exists.')
        print(f"Attempted to add existing player {nickname}.")
    finally:
        conn.close()
    print("add_player command handler defined.")

async def list_players(update, context):
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nickname, wins, losses FROM players")
    players = cursor.fetchall()
    conn.close()

    if not players:
        await update.message.reply_text('No players added yet. Use /add_player <nickname> to add one.')
        print("No players found in database.")
        return

    response = 'Current Players:\n'
    for nickname, wins, losses in players:
        response += f'- {nickname} (Wins: {wins}, Losses: {losses})\n'
    await update.message.reply_text(response)
    print("list_players command handler defined and players listed.")

async def remove_player(update, context):
    args = context.args
    if not args:
        await update.message.reply_text('Usage: /remove_player <nickname>')
        return
    nickname = args[0]

    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM players WHERE nickname = ?", (nickname,))
        conn.commit()
        if cursor.rowcount > 0:
            await update.message.reply_text(f'Player {nickname} removed successfully!')
            print(f"Player {nickname} removed.")
        else:
            await update.message.reply_text(f'Player {nickname} not found.')
            print(f"Attempted to remove non-existent player {nickname}.")
    finally:
        conn.close()
    print("remove_player command handler defined.")

async def predict_match(update, context):
    args = context.args
    if len(args) != 2:
        await update.message.reply_text('Usage: /predict <player1_nickname> <player2_nickname>')
        return

    player1_nickname = args[0]
    player2_nickname = args[1]

    conn = None
    try:
        conn = sqlite3.connect('players.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM players WHERE nickname = ?", (player1_nickname,))
        player1_data = cursor.fetchone()

        cursor.execute("SELECT * FROM players WHERE nickname = ?", (player2_nickname,))
        player2_data = cursor.fetchone()

        if player1_data and player2_data:
            p1_wins = player1_data[2]
            p1_losses = player1_data[3]
            p2_wins = player2_data[2]
            p2_losses = player2_data[3]

            prediction = predict_winner(p1_wins, p1_losses, p2_wins, p2_losses)
            await update.message.reply_text(f'Match between {player1_nickname} (Wins: {p1_wins}, Losses: {p1_losses}) and {player2_nickname} (Wins: {p2_wins}, Losses: {p2_losses}).\nPrediction: {prediction}')
            print(f"Prediction for {player1_nickname} vs {player2_nickname}: {prediction}.")
        elif not player1_data and not player2_data:
            await update.message.reply_text(f'Neither player {player1_nickname} nor {player2_nickname} found in the database.')
            print(f"Neither player {player1_nickname} nor {player2_nickname} found.")
        elif not player1_data:
            await update.message.reply_text(f'Player {player1_nickname} not found in the database.')
            print(f"Player {player1_nickname} not found.")
        else:  # not player2_data
            await update.message.reply_text(f'Player {player2_nickname} not found in the database.')
            print(f"Player {player2_nickname} not found.")
    except Exception as e:
        await update.message.reply_text(f'An error occurred: {e}')
        print(f"Error in predict_match: {e}")
    finally:
        if conn:
            conn.close()
    print("predict_match command handler defined.")

async def player_update(update, context):
    args = context.args

    if len(args) != 3:
        await update.message.reply_text('Usage: /player_update <nickname> <new_wins> <new_losses>')
        return

    nickname = args[0]

    try:
        new_wins = int(args[1])
        new_losses = int(args[2])
    except ValueError:
        await update.message.reply_text('Wins and losses must be integers.')
        return

    if new_wins < 0 or new_losses < 0:
        await update.message.reply_text('Wins and losses cannot be negative.')
        return

    conn = None
    try:
        conn = sqlite3.connect('players.db')
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE players SET wins = ?, losses = ? WHERE nickname = ?",
            (new_wins, new_losses, nickname)
        )
        conn.commit()

        if cursor.rowcount > 0:
            await update.message.reply_text(f'Player {nickname} updated successfully! New Wins: {new_wins}, New Losses: {new_losses}.')
            print(f"Player {nickname} updated to Wins: {new_wins}, Losses: {new_losses}.")
        else:
            await update.message.reply_text(f'Player {nickname} not found.')
            print(f"Attempted to update non-existent player {nickname}.")

    except sqlite3.Error as e:
        await update.message.reply_text(f'An error occurred with the database: {e}')
        print(f"Database error in player_update: {e}")
    except Exception as e:
        await update.message.reply_text(f'An unexpected error occurred: {e}')
        print(f"Unexpected error in player_update: {e}")
    finally:
        if conn:
            conn.close()
    print("player_update command handler defined.")

async def command_list(update, context):
    command_text = (
        "Available Commands:\n"
        "/start - Get a welcome message and basic instructions.\n"
        "/add_player <nickname> [wins] [losses] - Add a new player to the database. Wins and losses are optional.\n"
        "/list_players - List all players currently in the database with their stats.\n"
        "/remove_player <nickname> - Remove a player from the database.\n"
        "/predict <player1_nickname> <player2_nickname> - Get a prediction for a match between two players.\n"
        "/player_update <nickname> <new_wins> <new_losses> - Update a player's wins and losses.\n"
        "/command_list - Display this list of available commands."
    )
    await update.message.reply_text(command_text)
    print("command_list command handler defined.")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add_player", add_player))
application.add_handler(CommandHandler("list_players", list_players))
application.add_handler(CommandHandler("remove_player", remove_player))
application.add_handler(CommandHandler("predict", predict_match))
application.add_handler(CommandHandler("player_update", player_update))
application.add_handler(CommandHandler("command_list", command_list))
print("All command handlers re-added to the application dispatcher.")

print("Starting the bot...")
application.run_polling()
print("Bot stopped.")
