# Convenience functions for common connection management patterns
async def create_and_connect(
    host: str = "localhost", port: int = 1256, timeout: int = 10, server_bridge=None
) -> "ConnectionStatusManager":  # type: ignore # noqa: F821
    """
    Create connection manager and immediately attempt connection

    Returns:
        ConnectionStatusManager: Initialized and connected connection manager
    """
    config = ConnectionConfig(host=host, port=port, timeout_seconds=timeout)  # type: ignore # noqa: F821
    manager = ConnectionStatusManager(config, server_bridge)  # type: ignore # noqa: F821
    await manager.connect()
    return manager
