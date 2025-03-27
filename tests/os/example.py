"""Example usage of regulatory data access components."""
import asyncio
import logging
from datetime import datetime, timedelta

from src.data_access.dao.regulatory_dao import (RegulatoryDataType,
                                                RegulatoryJurisdiction)
from src.data_access.factory import factory
from src.data_access.sources.regulatory_data_source import RegulatoryDocument

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def dao_example():
    """Example using RegulatoryDAO."""
    logger.info("Running DAO example")

    # Get regulatory DAO
    regulatory_dao = factory.get_regulatory_dao(
        client_name="default", index_prefix="regulatory"
    )

    # Search for regulations
    search_result = await regulatory_dao.search_regulations(
        query_text="privacy data protection",
        data_type=RegulatoryDataType.REGULATION,
        jurisdiction=RegulatoryJurisdiction.EU,
        effective_date_start=datetime.now() - timedelta(days=365 * 5),  # Last 5 years
        page=1,
        size=10,
    )

    logger.info(f"Found {search_result.total} regulations")

    # Display the results
    for i, hit in enumerate(search_result.hits):
        logger.info(f"Result {i+1}: {hit['title']} ({hit['jurisdiction']})")

    # Get a specific regulation
    if search_result.hits:
        first_hit_id = search_result.hits[0]["id"]
        regulation = await regulatory_dao.get_regulation_by_id(first_hit_id)

        if regulation:
            logger.info(f"Retrieved regulation: {regulation['title']}")

            # Get related regulations
            related = await regulatory_dao.get_related_regulations(first_hit_id)
            logger.info(f"Found {len(related)} related regulations")

    # Get latest regulations
    latest = await regulatory_dao.get_latest_regulations(
        days=90, jurisdiction=RegulatoryJurisdiction.US  # Last 90 days
    )

    logger.info(f"Found {latest.total} regulations in the last 90 days")


async def data_source_example():
    """Example using RegulatoryDataSource."""
    logger.info("Running DataSource example")

    # Get regulatory data source
    data_source = factory.get_regulatory_data_source(
        client_name="default", index_prefix="regulatory"
    )

    # Create a new regulatory document
    new_doc = RegulatoryDocument(
        id="gdpr-2016-679",
        title="General Data Protection Regulation",
        data_type=RegulatoryDataType.REGULATION,
        jurisdiction=RegulatoryJurisdiction.EU,
        summary="Regulation on the protection of natural persons with regard to the processing of personal data.",
        effective_date=datetime(2018, 5, 25),
        publication_date=datetime(2016, 4, 27),
        issuing_body="European Parliament and Council",
        citation="Regulation (EU) 2016/679",
        url="https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        industries=["Technology", "Healthcare", "Finance", "Retail"],
        topics=["Data Protection", "Privacy", "Personal Data", "Consent"],
        keywords=["GDPR", "Data Protection", "Privacy"],
    )

    # Index the document
    try:
        result = await data_source.create(new_doc)
        logger.info(f"Created document with ID: {result.id}")
    except Exception as e:
        logger.error(f"Failed to create document: {str(e)}")

    # Search by text
    search_results = await data_source.search_by_text(
        text="data protection", jurisdiction=RegulatoryJurisdiction.EU
    )

    logger.info(f"Found {len(search_results)} documents about data protection")

    # Get by jurisdiction
    eu_docs = await data_source.get_by_jurisdiction(
        jurisdiction=RegulatoryJurisdiction.EU, data_type=RegulatoryDataType.REGULATION
    )

    logger.info(f"Found {len(eu_docs)} EU regulations")

    # Get by topics
    privacy_docs = await data_source.get_by_topics(
        topics=["Privacy", "Data Protection"], match_all=False
    )

    logger.info(f"Found {len(privacy_docs)} documents about privacy or data protection")

    # Get by effective date range
    recent_docs = await data_source.get_by_effective_date_range(
        start_date=datetime(2018, 1, 1), end_date=datetime.now()
    )

    logger.info(f"Found {len(recent_docs)} documents effective since 2018")


async def main():
    """Run examples."""
    try:
        # Run examples
        await dao_example()
        await data_source_example()
    finally:
        # Close all clients
        await factory.close_all_clients()


if __name__ == "__main__":
    asyncio.run(main())
