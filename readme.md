# KS-Bot-Test Discord Bot

KS-Bot is a Discord bot designed to track and display online status and locations of specific players in a gaming community. The bot also allows designated users to exclude or include players from being tracked.

## Features

- **Online Player Tracking:** Monitors and reports online status of players.
- **Location Reporting:** Displays last seen locations of tracked players.
- **Exclusion System:** Allows specified roles to exclude or include players from tracking.
- **Persistence:** Stores and retrieves tracking and exclusion data from AWS DynamoDB.
- **Customizable:** Uses environment variables for easy customization and deployment.

## Setup

### Prerequisites

- Python 3.12+
- Discord account and a Discord server
- AWS account with access to DynamoDB
- `boto3` and `discord.py` Python libraries

### Installation

1. **Clone the repository** or download the source code.

2. **Install required libraries:**

   ```bash
   pip install discord.py boto3
   ```

3. **Set up AWS credentials:** Create a new IAM user in AWS with programmatic access and permissions to read and write to a DynamoDB table. Configure your environment with the access key ID and secret access key.

4. **Create a DynamoDB table:** The table should have a single primary key named `id` of type String. The bot expects this table to store the `excluded_players` and `status_message_id` attributes.

5. **Configure environment variables:** Set the following environment variables in your environment or `.env` file:

   ```plaintext
   DISCORD_BOT_TOKEN=your_discord_bot_token
   DISCORD_SERVER_NAME=your_discord_server_name
   ONLINE_CHANNEL_NAME=your_online_channel_name
   REPORT_CHANNEL_NAME=your_report_channel_name
   DELIVERY_CHANNEL_NAME=your_delivery_channel_name
   EXCLUDE_GROUP_ROLE_NAME=your_exclude_group_role_name
   ```

### Running the Bot

Execute the bot by running:

```bash
python ks_bot_test.py
```

Ensure the bot is online in your Discord server and has permissions to read messages, send messages, and manage messages in the designated channels.

## Usage

- **Track Players:** The bot automatically tracks players' online status and locations based on messages in the specified channels.
- **Exclude Players:** Users with the specified role can exclude players from being tracked using the command `!ks exclude PlayerName`.
- **Include Players:** Similarly, they can include players back into tracking with `!ks include PlayerName`.

## Development

- **Custom Commands:** Extend the bot by adding more commands in the `ks_bot_test.py` script.
- **Logging:** Adjust logging levels and formats as per your needs for debugging or monitoring.
- **Data Management:** Modify how data is stored and retrieved from DynamoDB as per your requirements.

---

Remember to replace placeholders with actual values and paths. Adjust instructions and descriptions as per your project's specifics and requirements.
