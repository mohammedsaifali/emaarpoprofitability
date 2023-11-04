import streamlit as st
import pandas as pd

# Define a function to aggregate Amount_Sum and PurchaseAmount based on a list of invoice numbers
def aggregate_values_based_on_invoices(df, invoice_list, currency, conversion_rates):
    # Filter the DataFrame based on the given list of invoice numbers
    filtered_df = df[df['InvNo'].isin(invoice_list)]
    
    # Convert amounts if currency is not OMR
    conversion_rate = conversion_rates.get(currency, 1)  # Default to 1 if currency is OMR
    amount_sum = (filtered_df['Amount'].sum()) * conversion_rate
    purchase_amount_sum = (filtered_df['PurchaseAmount'].sum()) * conversion_rate
    
    return pd.Series({
        'Amount_Sum': amount_sum,
        'PurchaseAmount_Sum': purchase_amount_sum
    })

# Define a function to fetch the unique 'BillTo' based on a list of invoice numbers
def fetch_billto_based_on_invoices(df, invoice_list):
    # Filter the DataFrame based on the given list of invoice numbers
    filtered_df = df[df['InvNo'].isin(invoice_list)]
    return filtered_df['BillTo'].unique()[0] if not filtered_df.empty else None

# Function to process sales data
def process_sales_data(sales_register_file, sales_profitability_file):
    # Load Sales Register and Sales Profitability data
    sales_register_df = pd.read_excel(sales_register_file, skiprows=3)
    sales_profitability_df = pd.read_excel(sales_profitability_file, skiprows=3)

    # Define conversion rates
    conversion_rates = {
        'SAR': 0.1,
        'QAR': 0.11,
        'USD': 0.38
        # Add other currencies and rates if necessary
    }

    # Determine the currency for each PONo
    currency_per_po_df = sales_register_df.groupby('PONo')['Currency'].first().reset_index()

    re_aggregated_sales_profitability_df = sales_profitability_df.groupby(['InvNo', 'BillTo']).agg({
        'Amount': 'sum',
        'PurchaseAmount': 'sum'
    }).reset_index()

    # Aggregate DocNo (invoice numbers) as a list for each PONo
    aggregated_invoice_list_df = sales_register_df.groupby('PONo').agg({
        'DocNo': lambda x: ', '.join(map(str, x.unique()))
    }).reset_index()
    
    # Rename columns for clarity
    aggregated_invoice_list_df.columns = ['PONo', 'InvoiceNos_List']

    # Join the currency information with the aggregated invoice list
    aggregated_values_df = aggregated_invoice_list_df.merge(currency_per_po_df, on='PONo', how='left')

    # Modify the aggregation logic to include currency conversion
    aggregated_values_df['InvoiceNos_List'] = aggregated_values_df['InvoiceNos_List'].str.split(', ')
    aggregated_values_df[['Amount_Sum', 'PurchaseAmount_Sum']] = aggregated_values_df.apply(
        lambda x: aggregate_values_based_on_invoices(
            re_aggregated_sales_profitability_df, 
            x['InvoiceNos_List'], 
            x['Currency'], 
            conversion_rates
        ), 
        axis=1
    )

    # Fetch the 'BillTo' for each list of invoice numbers
    aggregated_values_df['BillTo'] = aggregated_values_df['InvoiceNos_List'].apply(
        lambda x: fetch_billto_based_on_invoices(re_aggregated_sales_profitability_df, x)
    )

    # Calculate Profit column as AmountAfterTax_Sum - PurchaseAmount_Sum
    aggregated_values_df['Profit'] = aggregated_values_df['Amount_Sum'] - aggregated_values_df['PurchaseAmount_Sum']

    return aggregated_values_df

# Streamlit app
def main():
    st.title("Emaar PO Profit Generator App")

    # File upload widgets
    st.sidebar.header("Upload Files")
    sales_register_file = st.sidebar.file_uploader("Upload Sales Register Excel File", type=["xls", "xlsx"])
    sales_profitability_file = st.sidebar.file_uploader("Upload Sales Profitability Excel File", type=["xls", "xlsx"])

    if sales_register_file and sales_profitability_file:
        if st.sidebar.button("Process Data"):
            st.sidebar.text("Processing data...")

            # Process the data
            processed_data_df = process_sales_data(sales_register_file, sales_profitability_file)

            st.sidebar.text("Data processing complete!")

            # Display the processed data in the app
            st.header("Processed Data")
            st.dataframe(processed_data_df)
            
            # Download button to download the processed data
            csv_data = processed_data_df.to_csv(index=False)
            st.download_button(
                label="Download Processed Data",
                data=csv_data,
                file_name="processed_data.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
