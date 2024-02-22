import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sqlalchemy.engine import URL
from sqlalchemy import create_engine
import datetime

def create_db_connection(server, database, username, password):
    """Creates and returns a database connection using SQLAlchemy."""
    connectionString = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": connectionString})
    engine = create_engine(connection_url)
    return engine

def top_sold_items(engine, no_of_items):
    """Fetches and returns top sold items."""
    topsolditem_query = f"""
    SELECT TOP {no_of_items} pm.productname, SUM(sd.Quantity) tot_qty
    FROM SaleDetail sd
    INNER JOIN ProductMaster pm ON sd.ProductID=pm.ProductID
    GROUP BY pm.ProductName
    ORDER BY tot_qty DESC;
    """
    return pd.read_sql(topsolditem_query, engine)

def top_customers(engine, no_of_customers):
    """Fetches and returns top customers."""
    topcustomers_query = f"""
    SELECT TOP {no_of_customers} cusm.CustomerName, SUM(slh.BillAmount) as TotalBillAmount, SUM(slh.TaxTotal) as TaxTotal
    FROM SaleHeader slh
    INNER JOIN CustomerMaster cusm ON slh.CustomerID=cusm.CustomerID
    WHERE cusm.CustomerName != '[None]'
    GROUP BY cusm.CustomerName
    ORDER BY TotalBillAmount DESC;
    """
    return pd.read_sql(topcustomers_query, engine)

# New function to fetch sales per customer
def sales_per_customers(engine, date_from, date_to):
    sales_per_customers_query = f"""
    SELECT cus.CustomerName, SUM(sh.BillAmount) AS BillTotal
    FROM SaleHeader sh
    INNER JOIN CustomerMaster cus ON sh.CustomerID = cus.CustomerID
    WHERE sh.voucherdate >= '{date_from}' AND sh.voucherdate <= '{date_to}'
    GROUP BY cus.CustomerName
    ORDER BY BillTotal DESC;
    """
    return pd.read_sql(sales_per_customers_query, engine)

# Function to plot donut chart with optional label removal
def plot_optional_donut_chart(df, label_to_remove=None):
    # If label_to_remove is provided, filter out the label and its corresponding value
    if label_to_remove:
        df_filtered = df[df['CustomerName'] != label_to_remove]
        labels = df_filtered['CustomerName']
        values = df_filtered['BillTotal']
    else:
        labels = df['CustomerName']
        values = df['BillTotal']

    plt.figure(figsize=(10, 8))  # Increase figure size

    # Explode slices for better readability
    explode = [0.1 if i == values.idxmax() else 0 for i in range(len(values))]
    
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, explode=explode, wedgeprops=dict(width=0.4))
    plt.axis('equal')  # Keep it a circle
    
    # Use a legend for better readability
    plt.legend(loc="best", bbox_to_anchor=(1, 1), labels=labels, title="Customers")
    
    plt.title('Sales Per Customer -  Donut Chart')

def app():
    st.title("Database Connection Setup")
    
    # Initialize session state for database connection
    if 'db_engine' not in st.session_state:
        st.session_state['db_engine'] = None

    # Database connection inputs
    server = st.text_input("Server", value="HOSERVER")
    database = st.text_input("Database", value="FR8DemoDB")
    username = st.text_input("Username", value="sa")
    password = st.text_input("Password", value="123", type="password")

    if st.button("Connect"):
        # Create and store the database connection in session state
        st.session_state.db_engine = create_db_connection(server, database, username, password)
        st.success("Connected Successfully")

    if st.session_state.db_engine:
        try:
            # Use the existing database connection from session state
            engine = st.session_state.db_engine

            # Fetch top sold items and display in DataFrame
            no_of_items_sold = st.number_input("How many top sold items do you want to see?", min_value=1, value=5)
            df_top_sold_items = top_sold_items(engine, no_of_items_sold)
            st.subheader("Top Sold Items")
            st.write(df_top_sold_items)

            # Create Seaborn bar chart for top sold items
            st.subheader("Top Sold Items Visualization")
            fig_sold_items, ax_sold_items = plt.subplots()
            ax_sold_items = sns.barplot(data=df_top_sold_items, x="tot_qty", y="productname", estimator="sum",hue="tot_qty")
            ax_sold_items.bar_label(ax_sold_items.containers[0], fontsize=10)
            ax_sold_items.set_xticklabels(ax_sold_items.get_xticklabels(), rotation=90, ha="right")
            plt.tight_layout()
            st.pyplot(fig_sold_items)

            # Fetch top customers and display in DataFrame
            no_of_customers = st.number_input("How many top customers do you want to see?", min_value=1, value=5)
            df_top_customers = top_customers(engine, no_of_customers)
            st.subheader("Top Customers")
            st.write(df_top_customers)

            

            # Create Seaborn bar chart for top customers
            st.subheader("Top Customers Visualization")

            # Style settings
            sns.set_palette("viridis")
            sns.set_style("whitegrid")

            # Create a beautiful bar chart
            fig_customers, ax_customers = plt.subplots(figsize=(10, 6))
            ax_customers = sns.barplot(data=df_top_customers, x="TotalBillAmount", y="CustomerName", estimator="sum", ci=None, palette="viridis", saturation=0.75)
            ax_customers.bar_label(ax_customers.containers[0], fontsize=10, fmt="%d")  # Display labels with integer formatting

            # Customize labels and ticks
            ax_customers.set_xlabel("Total Bill Amount", fontsize=12, fontweight="bold")
            ax_customers.set_ylabel("Customer Name", fontsize=12, fontweight="bold")
            ax_customers.tick_params(axis="both", labelsize=10)

            plt.tight_layout()
            st.pyplot(fig_customers)

            # New section for sales per customer
            st.subheader("Sales Per Customer")
            date_from = st.date_input("From Date", datetime.date(2020, 1, 1))
            date_to = st.date_input("To Date", datetime.date(2023, 12, 31))
            
            # Fetch sales per customer data
            df_sales_per_customer = sales_per_customers(engine, date_from, date_to)
            st.write(df_sales_per_customer)

            # Get the list of unique customer names for user selection
            all_customer_names = df_sales_per_customer['CustomerName'].unique().tolist()

            # Display an optional message for removal
            remove_customer = st.checkbox("Remove a specific customer")

            if remove_customer:
                # Allow the user to select a customer to remove
                selected_customer = st.selectbox("Select a customer to remove:", ['None'] + all_customer_names)

                if selected_customer != 'None':
                    # Visualization with optional removal
                    st.subheader("Sales Per Customer Visualization (excluding selected customer)")
                    plot_optional_donut_chart(df_sales_per_customer, selected_customer)
                    st.pyplot(plt.gcf())
                else:
                    # Visualization without removal
                    st.subheader("Sales Per Customer Visualization")
                    plot_optional_donut_chart(df_sales_per_customer)
                    st.pyplot(plt.gcf())
            else:
                # Visualization without removal
                st.subheader("Sales Per Customer Visualization")
                plot_optional_donut_chart(df_sales_per_customer)
                st.pyplot(plt.gcf())

                
        except Exception as e:
            st.error(f"Failed to connect or retrieve data: {e}")
    else:
        st.warning("Please connect to the database.")

if __name__ == "__main__":
    app()
