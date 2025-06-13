import datetime

import streamlit as st

from app.modules.data_manipulation.query_repository.checkout_queries import (
    get_checkout_count,
)
from app.modules.data_manipulation.query_repository.checkout_tracker_queries import (
    get_checkout_tracker_count,
)
from app.modules.data_manipulation.query_repository.cloud_blob_queries import get_cloud_blob_count, get_cloud_blob_df
from app.modules.data_manipulation.query_repository.transaction_queries import (
    get_transaction_count,
)
from app.modules.duckdb.duckdb_tables import duckdb_table_summary, table_exists
from app.page.cached_resources.azure_connection import get_azure_connection
from app.page.lib.core_heath_check import get_core_client
from app.systems.ingestion.cloud_to_duckdb import CloudSyncManager
from app.systems.ingestion.core_to_duckdb import (
    CoreSyncTransactionManager,
    CoreSyncCheckoutManager,
    CoreSyncCheckoutTrackerManager,
)


@st.fragment(run_every=datetime.timedelta(seconds=5))
def duck_db_status_fixture():
    with st.container(border=True):
        st.header("Duck Context")
        st.caption("Running DuckDB statistics")
        st.write(f"Updated {datetime.datetime.now(datetime.timezone.utc).time()}")

        st.markdown("### Tables and their statistics")
        st.dataframe(duckdb_table_summary())


def duckdb_ingestion_analytics():
    tables = ("HubTransaction", "HubCheckout", "HubCheckoutTracker")

    with st.container(border=True):
        st.header("Core")
        for table_name, col in zip(tables, st.columns(len(tables)), strict=False):
            with col.container(border=True):
                st.markdown(f"#### {table_name}")

                #
                in_db = table_exists(table_name=table_name.lower())
                in_db_txt = ":green[Yes]" if in_db else ":red[No]"
                st.write(f"Present in database: {in_db_txt}")

                #
                st.write("Automatic Sync")
                toggle_key = f"ingest_{table_name.lower()}"
                st.toggle(
                    key=toggle_key,
                    label="Enable auto sync",
                    value=st.session_state.get(toggle_key, False),
                )

                #
                st.button("Sync once", key=toggle_key + "_sync_once")


def duck_ingestion_page():
    core = get_core_client()

    # -----
    # Data ingestion
    # fixme this should be moved to a global component
    if st.session_state.get("ingest_hubtransaction_sync_once", False):
        CoreSyncTransactionManager().sync_once(from_scratch=True)
    if st.session_state.get("ingest_hubcheckout_sync_once", False):
        CoreSyncCheckoutManager().sync_once(from_scratch=True)
    if st.session_state.get("ingest_hubcheckouttracker_sync_once", False):
        CoreSyncCheckoutTrackerManager().sync_once(from_scratch=True)
    if st.session_state.get("ingest_cloudblob_sync_once", False):
        CloudSyncManager().sync_once(from_scratch=True, query_blob_properties=True)

    # -----
    st.title("Data Ingestion")
    st.caption(
        "Continuous monitoring tool for loading data from different services into duckdb for analytics"
    )

    # DuckDB Statistics
    duck_db_status_fixture()

    # Ingestion configuration
    duckdb_ingestion_analytics()  # General overview

    with st.container(border=True):
        st.header("HubTransaction")
        st.caption("HubTransaction synced status")

        is_table = table_exists(table_name="hubtransaction")
        in_table_txt = ":green[Yes]" if is_table else ":red[No]"
        st.write(f"Present in database: {in_table_txt}")

        if is_table:
            trans_count = get_transaction_count()
            core_trans_count = core.count_transactions()
            st.write(f"{trans_count} out of {core_trans_count}")

    with st.container(border=True):
        st.header("HubCheckout")
        st.caption("HubCheckout synced status")

        is_table = table_exists(table_name="hubcheckout")
        in_table_txt = ":green[Yes]" if is_table else ":red[No]"
        st.write(f"Present in database: {in_table_txt}")

        if is_table:
            checkout_count = get_checkout_count()
            core_checkout_count = core.count_hubcheckouts()
            st.write(f"{checkout_count} out of {core_checkout_count}")

    with st.container(border=True):
        st.header("HubCheckoutTracker")
        st.caption("HubCheckoutTracker synced status")

        is_table = table_exists(table_name="hubcheckouttracker")
        in_table_txt = ":green[Yes]" if is_table else ":red[No]"
        st.write(f"Present in database: {in_table_txt}")

        if is_table:
            checkout_tracker_count = get_checkout_tracker_count()
            core_checkout_tracker_count = core.count_hubcheckouttrackers()
            st.write(f"{checkout_tracker_count} out of {core_checkout_tracker_count}")

    with st.container(border=True):
        st.header("Cloud Blobs")
        st.caption("Cloud Blobs synced status")

        is_table = table_exists(table_name="cloudblob")
        in_table_txt = ":green[Yes]" if is_table else ":red[No]"
        st.write(f"Present in database: {in_table_txt}")

        if is_table:
            cloud_client = get_azure_connection()
            cloud_blob_count = CloudSyncManager.fetch_data_count(cloud_client=cloud_client)
            cloud_duck_count = get_cloud_blob_count()
            st.write(f"{cloud_duck_count} out of {cloud_blob_count}")

        st.button("Sync once", key="ingest_cloudblob_sync_once")

        if is_table:
            st.dataframe(get_cloud_blob_df(limit=100))
