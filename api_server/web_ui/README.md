# CyberBackup 3.0 Web GUI

A modern, responsive web interface for the CyberBackup encrypted file backup system.

## Features

- **Modern Web Interface**: Clean, Material Design-inspired UI with dark/light themes
- **Real-time Updates**: WebSocket communication with Socket.IO for live progress updates
- **File Management**: Drag-and-drop file selection with validation and metadata display
- **Progress Tracking**: Visual progress indicators with ETA calculations and speed monitoring
- **Connection Monitoring**: Real-time connection health and latency tracking
- **Error Handling**: Comprehensive error boundaries with user-friendly messages
- **Accessibility**: ARIA support and screen reader compatibility
- **Logging System**: Real-time logs with filtering and export capabilities
- **Responsive Design**: Works on desktop and mobile devices

## Architecture

- **Single Page Application**: `index.html` is the canonical single-page implementation
- **Consolidated Assets**: All CSS consolidated into `css/styles.css`, all JavaScript organized into `js/` directory
- **Pure Vanilla JavaScript**: No module bundlers, modern defer loading for optimal performance
- **Modular Design**: Four main JavaScript bundles for clean separation:
  - `core-utils.js` - DOM utilities, formatters, and state management
  - `services.js` - API client, WebSocket, and service layer
  - `app.js` - Main application logic and UI binding
  - `enhancements.js` - UI enhancements and advanced features
- **Error Boundaries**: Robust error handling and recovery mechanisms
- **Performance Optimized**: Efficient DOM updates and memory management
- **Security**: Input validation and XSS protection

## Quick Start

### Prerequisites

- Node.js 16.0.0 or higher
- A compatible web browser (Chrome 90+, Firefox 88+, Safari 14+)

### ⚠️ Important: Must Run via HTTP Server

**Do NOT open the HTML file directly from your filesystem** (`file://` protocol).
The application requires an HTTP server because:
- Browsers block API requests from `file://` origins (CORS security)
- WebSocket connections require HTTP/HTTPS protocols

### Recommended: Use the API Server (Serves Both API and UI)

```bash
# From the project root
python api_server/cyberbackup_api_server.py
```
Then open: **http://localhost:9090**

This runs the Flask API server which also serves the web UI - no additional setup needed.

### Alternative: Static Server + API Server

If you want to serve the UI separately for development:

```bash
# Terminal 1: Start the API server (port 9090)
python api_server/cyberbackup_api_server.py

# Terminal 2: Start a static file server (port 9091)
cd api_server/web_ui
npx http-server -p 9091 -c-1 .
```
Then open: **http://localhost:9091**

The UI automatically detects cross-origin scenarios and routes API calls to port 9090.

### VS Code Tasks

You can also use the pre-configured VS Code tasks:
- **`Client Web GUI + API Server`** - Starts the API server and opens the web GUI in browser
- **`Client Web GUI (Static Only - No API)`** - Starts just the static file server (for UI testing without API)

## Usage

1. **Configure Connection**: Enter the server address and username
2. **Select File**: Drag and drop a file or click "Choose File"
3. **Start Backup**: Click "Connect / Start" to begin the backup process
4. **Monitor Progress**: View real-time progress, logs, and statistics

## Development

### Project Structure

```
web_ui/
├── js/                # JavaScript bundles (consolidated)
│   ├── core-utils.js  # DOM utilities, formatters, state management
│   ├── services.js    # API client, WebSocket, service layer
│   ├── app.js         # Main application logic
│   └── enhancements.js # UI enhancements and effects
├── css/               # Stylesheets (consolidated)
│   └── styles.css     # All CSS (theme, layout, components)
├── backup/            # Archived legacy implementations
├── index.html         # Main application page
├── favicon.svg        # Application icon
├── package.json       # Project configuration
└── README.md          # This file
```

### Available Scripts

```bash
# Development
npm run dev          # Start development server with hot reload
npm start            # Start production server

# Validation and Quality
npm run validate     # Validate all modules and dependencies
npm run check        # Run all quality checks
npm run clean        # Clean temporary files

# Build
npm run build        # Validate and lint the project
```

### Code Style

- **Consolidated Bundles**: JavaScript organized into four main bundles for optimal loading
- **Defer Loading**: Scripts loaded with `defer` attribute for non-blocking page load
- **Error Boundaries**: All async operations wrapped in error handling
- **Clean Architecture**: Separation of concerns with clear functional boundaries
- **Documentation**: Functions and classes should have JSDoc comments
- **Accessibility**: All interactive elements have proper ARIA attributes

## API Integration

The web GUI communicates with the CyberBackup server via:

1. **HTTP API**: REST endpoints for control operations
2. **WebSocket**: Real-time updates and progress notifications
3. **File Upload**: Chunked file transfer with progress tracking

### Server Configuration

The GUI expects a CyberBackup server running on the configured port (default: 1256).

## Error Handling

The application includes comprehensive error handling:

- **Network Errors**: Automatic retry with exponential backoff
- **UI Errors**: Graceful degradation with fallback functionality
- **File Errors**: Detailed error messages for validation failures
- **Connection Errors**: Real-time connection monitoring and recovery

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Security Considerations

- All user inputs are validated and sanitized
- File uploads are checked for size and type restrictions
- WebSocket connections use secure protocols when available
- No sensitive data is stored in browser localStorage

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure the CyberBackup server is running and accessible
2. **File Upload Fails**: Check file size limits and server permissions
3. **WebSocket Errors**: Verify firewall settings and port availability
4. **Script Loading Errors**: Ensure all files in `js/` and `css/` directories are present

### Debug Mode

Enable debug logging by opening browser developer tools and checking the console output.

## Contributing

1. Follow the existing code style and architecture patterns
2. Add error boundaries for any new async operations
3. Include proper accessibility attributes for new UI elements
4. Test with both light and dark themes
5. Validate all changes with `npm run validate`

## License

MIT License - see LICENSE file for details.

## Support

For issues and support, please refer to the main CyberBackup project documentation.