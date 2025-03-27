@dataclass
class OpenSearchConfig:
    """Configuration for OpenSearch client."""

    hosts: List[str]
    username: Optional[str] = None
    password: Optional[str] = None
    aws_region: Optional[str] = None
    use_ssl: bool = True
    verify_certs: bool = True
    connection_timeout: int = 10
    max_retries: int = 3
    retry_on_timeout: bool = True


class OpenSearchClient:
    """Abstract client for OpenSearch operations."""

    def __init__(self, config: OpenSearchConfig):
        """Initialize OpenSearch client.

        Args:
            config: OpenSearch configuration
        """
        self.config = config
        self.client_args = {
            "hosts": config.hosts,
            "use_ssl": config.use_ssl,
            "verify_certs": config.verify_certs,
            "connection_timeout": config.connection_timeout,
            "max_retries": config.max_retries,
            "retry_on_timeout": config.retry_on_timeout,
        }

        # Configure authentication
        if config.username and config.password:
            self.client_args["http_auth"] = (config.username, config.password)
        elif config.aws_region:
            # Use AWS IAM authentication if AWS region is provided
            from opensearchpy import AWSIAM

            self.client_args["http_auth"] = AWSIAM(config.aws_region)

        self._client = None
