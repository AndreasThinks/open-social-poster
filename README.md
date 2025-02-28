# Social Poster

An open-source, unified social media management tool that lets you post content and media to multiple platforms simultaneously.

## Features

- **Multi-platform Support**: Post to Bluesky, Twitter/X, and Mastodon from a single interface
- **Media Uploads**: Attach images and other media files to your posts
- **Character Limit Checking**: Real-time validation of post length against platform limits

## Installation and Running

This project uses [UV](https://docs.astral.sh/uv/) for managing Python dependencies and execution. Two convenience scripts are provided to handle UV installation and run the main script.

### Windows

Right click run_social_poster.ps1 and select Open in Powershell, or

1. Open PowerShell
2. Run the provided script by right clicking:
```powershell
powershell -ExecutionPolicy ByPass -File run_social_poster.ps1
```

### macOS/Linux

1. Open a terminal
2. Make the script executable:
```bash
chmod +x run_social_poster.sh
```
3. Run the script:
```bash
./run_social_poster.sh
```

## Usage

1. **Connect Accounts**: First, connect to your social media accounts in the Accounts tab
   - For Bluesky: Enter your handle and app password
   - For Twitter/X: Login through the browser window that opens
   - For Mastodon: Enter your instance domain and authorize the application

2. **Create Posts**: Switch to the Post tab to compose your message
   - Add media files using the upload section
   - Type your message in the text area
   - Select which connected accounts to post to

3. **Monitor Character Limits**: The app will automatically check if your post exceeds character limits for selected platforms

4. **Send**: Click the Post button to send your message to all selected platforms

## Technical Details

Social Poster is built using:
- **FastHTML**: Server-side rendering framework
- **MonsterUI**: Component library for clean, responsive UI
- **HTMX**: Dynamic interactions without writing JavaScript
- **ATProto**: For Bluesky API integration
- **Selenium**: For Twitter/X integration
- **Mastodon API**: For Mastodon integration
- **SQLite**: Local storage of account information

## Troubleshooting

- **Connection Issues**: Ensure you have a stable internet connection and that the social media services are accessible.
- **Authentication Failures**: For Bluesky, verify you're using a valid app password. For Twitter, ensure your account is not locked.
- **Upload Problems**: Check that your media files are in supported formats and under size limits.
- **Browser Issues**: For Twitter integration, ensure Chrome is installed and up to date.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.