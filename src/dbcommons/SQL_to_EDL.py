"""
Copyright (c) 2026 Stephanie Johnson

TODO this has a couple bugs - 
amount numeric(12,2) NOT NULL,
UNIQUE (accnt_id, date, amount)

outputs as:
Amount numeric(122)
UNIQUE (accnt_id

"""

import os, sys
import re

def convert_name(name_sql: str) -> str:
    """
    Convert SQL schema table or column name in my convention (all lower case, underscores between words)
    to EDL (capitalize each word, no underscores)

    Parameters
    ----------
    name_sql: str
        SQL equivalent
    
    Returns
    -------
    str
        EDL equivalent
        
    """
    # Capitalize first letter
    name_edl = name_sql[0].upper()+ name_sql[1:]
    name_edl = re.sub(r"_\w",lambda x: name_edl[x.start()+1].upper(),name_edl)

    return name_edl


def convert_to_EDL(schema_file_path: str) -> str:
    """
    Convert the SQL in a schema file to the EDL used for generating schema diagram
    at https://app.quickdatabasediagrams.com.

    Given this SQL:

    CREATE TABLE order(
        id SERIAL PRIMARY KEY,
        customer_id integer REFERENCES customer(id),
        total_amount money NOT NULL,
        order_status_id integer REFERENCES order_status(id)
    );

    this is the equivalent EDL (probably caps don't matter but they're easier to read with no underscores):

    Order
    -
    OrderID PK int
    CustomerID int FK >- Customer.CustomerID
    TotalAmount money
    OrderStatusID int FK >- OrderStatus.OrderStatusID
    
    Parameters
    __________
    schema_file_path: str
        File path to SQL schema    
    
    Return
    ______
    str
        Path to file with EDL equivalent
    """
    
    # SQL:EDL type equivalents
    type_conversions = {
        "integer":"int", 
        "text": "string"
        }

    if not os.path.isfile(schema_file_path):
        # Laziness, not bothering with a logger for this
        print(f"convert_to_EDL: {schema_file_path} not a path to a file that exists")
        return None
    if not os.path.splitext(schema_file_path)[1] == ".sql":
        print(f"convert_to_EDL: {schema_file_path} not a sql file")
        return None
    
    output_file_path = os.path.splitext(schema_file_path)[0]+"_EDL.txt"
    
    with open(schema_file_path, "r") as f:
        sql_lines = list(f)
    
    edl_lines = []

    # take only the CREATE TABLEs - EDL can't do CREATE TYPE or such
    create_start_idxs = [s for s in range(0,len(sql_lines)) if sql_lines[s][:12] == "CREATE TABLE"]
    statement_ends_idxs = [e for e in range(0,len(sql_lines)) if re.search(r"\);", sql_lines[e]) is not None]

    for s in create_start_idxs:
        # Replace the CREATE TABLE statement and ID line with EDL equivalents:
        table_name = sql_lines[s][13:-2]
        table_name = convert_name(table_name)
        edl_lines.append(table_name)
        edl_lines.append("-")
        edl_lines.append(table_name+"ID PK int")

        # Convert the rest of the lines in this create table statement
        end_idx = [k for k in statement_ends_idxs if k>s][0]
        for e in range(s+2,end_idx):
            next_elements = sql_lines[e].split()
            col_name = next_elements[0]
            col_name = convert_name(col_name)

            col_type = next_elements[1]
            # Strip a trailing comma, if present
            col_type = re.sub(",","",col_type)
            if col_type in type_conversions:
                col_type = type_conversions[col_type]

            new_line = col_name + " " + col_type

            if len(next_elements) > 2:
                for n in range(2,len(next_elements)):
                    if next_elements[n] == "REFERENCES":
                        # Unfortunate special case: this means the end of col_name is now Id, needs to be ID
                        col_name = col_name[:-1] + col_name[-1].upper()
                        new_line = col_name + " " + col_type
                        ref_table_name = next_elements[n+1].split("(")[0]
                        ref_table_name = convert_name(ref_table_name)
                        ref_piece = " FK >- " + ref_table_name + "." + ref_table_name + "ID"
                        new_line = new_line + ref_piece
                        break
                    # else: EDL won't take things like "UNIQUE", "NOT NULL" so just ignore those (drop them)

            edl_lines.append(new_line)
        edl_lines.append("\n")
    
    edl_out = "\n".join(edl_lines)

    with open(output_file_path, "w") as out_f:
        out_f.write(edl_out)

    return output_file_path
    


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise ValueError("SQL_to_EDL.py takes exactly one input arg (path to SQL file)")
    
    output_file_path = convert_to_EDL(schema_file_path=sys.argv[1])