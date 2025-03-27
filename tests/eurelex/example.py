"""Example usage of regulations data access components."""
import asyncio
import logging
from datetime import datetime

from src.data_access.dao.regulations_dao import RegulationSearchRequest
from src.data_access.factory import factory
from src.data_access.sources.regulatory_document import RegulationDocument

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def get_regulation_by_id():
    """Example of getting regulation by ID."""
    # Get regulations DAO
    regulations_dao = factory.get_regulations_dao(index_prefix="regulations-test")

    # Exact ID example
    regulation_id = "doc=02013R0575-20190101/lang=en/part=00003/title=00007/chap=00015/sec=00029/ssec=00022/art=00220"

    # Get regulation by ID
    regulation = await regulations_dao.get_regulation_by_id(regulation_id)

    if regulation:
        logger.info(f"Found regulation: {regulation['title']}")
        logger.info(f"Full name: {regulation['full_name']}")
        logger.info(f"Document type: {regulation['document_type']}")
        logger.info(f"CELEX: {regulation['celex']}")

        # Extract document parts
        if "/" in regulation_id:
            parts = {}
            for segment in regulation_id.split("/"):
                if "=" in segment:
                    key, value = segment.split("=", 1)
                    parts[key] = value

            logger.info(f"Document parts: {parts}")
    else:
        logger.info(f"Regulation not found with ID: {regulation_id}")


async def get_related_regulations():
    """Example of getting related regulations using wildcard ID search."""
    # Get regulations DAO
    regulations_dao = factory.get_regulations_dao(index_prefix="regulations-test")

    # Base regulation ID
    regulation_id = "doc=02013R0575-20190101/lang=en/part=00003/title=00007/chap=00015/sec=00029/ssec=00022/art=00220"

    # Get related regulations
    related = await regulations_dao.get_related_regulations(
        regulation_id=regulation_id, language="en", max_results=10
    )

    logger.info(f"Found {len(related)} related regulations")

    # Display related regulations
    for i, rel in enumerate(related[:5], 1):  # Show first 5
        logger.info(f"Related {i}: {rel['name']} - {rel['title']}")


async def search_regulations():
    """Example of searching regulations."""
    # Get regulations DAO
    regulations_dao = factory.get_regulations_dao(index_prefix="regulations-test")

    # Create search request
    search_request = RegulationSearchRequest(
        query_text="Volatility Adjustments",
        kind="article",
        language="en",
        legally_binding=True,
        page=1,
        size=10,
        sort_by="position",
        sort_order="asc",
    )

    # Search regulations
    results = await regulations_dao.search_regulations(search_request)

    logger.info(f"Found {results.total} regulations matching the search criteria")

    # Display search results
    for i, result in enumerate(results.hits[:5], 1):  # Show first 5
        logger.info(f"Result {i}: {result['name']} - {result['title']}")
        if "enforced_date_range" in result:
            date_range = result["enforced_date_range"]
            logger.info(
                f"  Enforced from {date_range.get('gte')} to {date_range.get('lte')}"
            )


async def get_regulation_hierarchy():
    """Example of getting the complete hierarchy of a regulation."""
    # Get regulations DAO
    regulations_dao = factory.get_regulations_dao(index_prefix="regulations-test")

    # Get regulation hierarchy by CELEX
    celex = "02013R0575-20190101"

    hierarchy = await regulations_dao.get_regulation_hierarchy(
        celex=celex, language="en"
    )

    logger.info(f"Found {hierarchy.total} parts in the regulation hierarchy")

    # Count by kind
    kinds = {}
    for item in hierarchy.hits:
        kind = item["kind"]
        kinds[kind] = kinds.get(kind, 0) + 1

    logger.info("Hierarchy composition:")
    for kind, count in kinds.items():
        logger.info(f"  {kind}: {count} items")


async def data_source_example():
    """Example using the RegulationsDataSource directly."""
    # Get regulations data source
    data_source = factory.get_regulations_data_source(index_prefix="regulations-test")

    # Search by text
    text_results = await data_source.search_by_text(
        text="Supervisory Volatility", language="en"
    )

    logger.info(f"Found {len(text_results)} documents matching text search")

    # Get by wildcard ID
    wildcard_results = await data_source.get_by_wildcard_id(
        id_pattern="doc=02013R0575-20190101/lang=en/*/art=*", language="en"
    )

    logger.info(f"Found {len(wildcard_results)} documents matching wildcard pattern")

    # Get related articles
    base_id = "doc=02013R0575-20190101/lang=en"
    articles = await data_source.get_related_articles(
        regulation_id=base_id, language="en"
    )

    logger.info(f"Found {len(articles)} related articles")

    # Get document hierarchy
    hierarchy = await data_source.get_document_hierarchy(
        document_id="doc=02013R0575-20190101", language="en"
    )

    logger.info("Document hierarchy by kind:")
    for kind, items in hierarchy.items():
        logger.info(f"  {kind}: {len(items)} items")


async def main():
    """Run examples."""
    try:
        # Run examples
        logger.info("=== Getting regulation by ID ===")
        await get_regulation_by_id()

        logger.info("\n=== Getting related regulations ===")
        await get_related_regulations()

        logger.info("\n=== Searching regulations ===")
        await search_regulations()

        logger.info("\n=== Getting regulation hierarchy ===")
        await get_regulation_hierarchy()

        logger.info("\n=== Using data source directly ===")
        await data_source_example()

    finally:
        # Close all clients
        await factory.close_all_clients()


if __name__ == "__main__":
    asyncio.run(main())
