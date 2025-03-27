class DataAccessFactory:
    # ...

    def get_opensearch_client(
        self, name: str = "default", config: Optional[OpenSearchConfig] = None
    ) -> OpenSearchClient:
        """Get an OpenSearch client.

        Args:
            name: Client name
            config: OpenSearch configuration

        Returns:
            OpenSearchClient: OpenSearch client
        """
        if name in self._clients:
            return self._clients[name]

        # Create default config if not provided
        if config is None:
            config = OpenSearchConfig(
                hosts=self._get_hosts_from_env(),
                username=os.environ.get("OPENSEARCH_USERNAME"),
                password=os.environ.get("OPENSEARCH_PASSWORD"),
                aws_region=os.environ.get("AWS_REGION"),
            )

        # Create client
        client = OpenSearchClient(config)

        self._clients[name] = client
        return client
