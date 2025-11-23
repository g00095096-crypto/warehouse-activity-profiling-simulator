import pandas as pd
import numpy as np

def run_slotting(sku_raw: pd.DataFrame,
                 lines_df: pd.DataFrame,
                 zone_raw: pd.DataFrame):
    """
    Run the heuristic slotting aligned with min Σ λ_j * d_k.
    Returns:
      - assignment_df
      - zone_utilization_df
      - total_travel_cost
      - zone_demand (for bar chart)
      - heat_pivot (for heatmap)
    """

    # --- Standardize columns ---
    sku_raw = sku_raw.rename(columns={
        "sku_id": "SKU_ID",
        "SKU Id": "SKU_ID",
        "Weekly_Demand_units": "Weekly_Demand_units",
        "weekly_demand_units": "Weekly_Demand_units",
        "Unit_Vol_m3": "Unit_Vol_m3",
        "unit_vol_m3": "Unit_Vol_m3",
        "Storage_Zone": "Storage_Type",
        "storage_zone": "Storage_Type",
        "Storage_Type": "Storage_Type",
        "ABC_Class": "ABC_Class"
    })

    lines_df = lines_df.rename(columns={
        "order_id": "Order_ID",
        "sku_id": "SKU_ID",
        "qty": "Qty"
    })

    zone_raw = zone_raw.rename(columns={
        "Zone_ID": "Zone_ID",
        "Storage_Type": "Storage_Type",
        "Capacity": "Capacity_m3",
        "Distance": "Distance_m"
    })

    # --- Demand per SKU (λ_j) ---
    sku_demand = (
        lines_df
        .groupby("SKU_ID")["Qty"]
        .sum()
        .reset_index()
        .rename(columns={"Qty": "TotalQty_Ordered"})
    )

    sku_df = sku_raw.merge(sku_demand, on="SKU_ID", how="left")
    sku_df["TotalQty_Ordered"]    = sku_df["TotalQty_Ordered"].fillna(0)
    sku_df["Weekly_Demand_units"] = sku_df["Weekly_Demand_units"].fillna(0)

    # λ_j = Weekly demand
    sku_df["Lambda_Weekly"] = sku_df["Weekly_Demand_units"]

    sku_df = sku_df[[
        "SKU_ID",
        "TotalQty_Ordered",
        "Lambda_Weekly",
        "Unit_Vol_m3",
        "Storage_Type",
        "ABC_Class"
    ]].copy()

    sku_df["Unit_Vol_m3"] = sku_df["Unit_Vol_m3"].fillna(0.01)

    # --- Zone table ---
    zone_df = zone_raw[[
        "Zone_ID",
        "Storage_Type",
        "Capacity_m3",
        "Distance_m"
    ]].copy()

    zone_df["Remaining_Capacity_m3"] = zone_df["Capacity_m3"].astype(float)

    # sort zones within type by distance (closest first)
    zone_df = zone_df.sort_values(
        ["Storage_Type", "Distance_m"],
        ascending=[True, True]
    ).reset_index(drop=True)

    # --- Heuristic assignment ---
    assignments = []

    sku_sorted = sku_df.sort_values(
        "Lambda_Weekly", ascending=False
    ).reset_index(drop=True)

    for _, sku_row in sku_sorted.iterrows():
        sku_id   = sku_row["SKU_ID"]
        lam_j    = float(sku_row["Lambda_Weekly"])
        sku_vol  = float(sku_row["Unit_Vol_m3"])
        sku_type = sku_row["Storage_Type"]
        sku_abc  = sku_row.get("ABC_Class", None)

        compatible_zones = zone_df[zone_df["Storage_Type"] == sku_type].copy()
        assigned_zone_id = None

        for _, z_row in compatible_zones.iterrows():
            if z_row["Remaining_Capacity_m3"] >= sku_vol:
                assigned_zone_id = z_row["Zone_ID"]

                zone_df.loc[zone_df["Zone_ID"] == assigned_zone_id,
                            "Remaining_Capacity_m3"] = (
                    z_row["Remaining_Capacity_m3"] - sku_vol
                )
                break

        assignments.append({
            "SKU_ID": sku_id,
            "Assigned_Zone": assigned_zone_id,
            "Storage_Type": sku_type,
            "Demand_Lambda_Weekly": lam_j,
            "TotalQty_Ordered": float(sku_row["TotalQty_Ordered"]),
            "Unit_Vol_m3": sku_vol,
            "ABC_Class": sku_abc
        })

    assignment_df = pd.DataFrame(assignments)

    # --- Zone utilization ---
    assigned_volume = (
        assignment_df
        .dropna(subset=["Assigned_Zone"])
        .groupby("Assigned_Zone")["Unit_Vol_m3"]
        .sum()
        .reset_index()
        .rename(columns={"Unit_Vol_m3": "Used_Volume_m3"})
    )

    zone_util = zone_df.merge(
        assigned_volume,
        left_on="Zone_ID",
        right_on="Assigned_Zone",
        how="left"
    )

    zone_util["Used_Volume_m3"] = zone_util["Used_Volume_m3"].fillna(0.0)
    zone_util["Remaining_Capacity_m3_calc"] = (
        zone_util["Capacity_m3"] - zone_util["Used_Volume_m3"]
    )
    zone_util["Utilization_pct"] = (
        (zone_util["Used_Volume_m3"] / zone_util["Capacity_m3"]) * 100.0
    ).round(2)

    zone_utilization_df = zone_util[[
        "Zone_ID",
        "Storage_Type",
        "Capacity_m3",
        "Used_Volume_m3",
        "Remaining_Capacity_m3_calc",
        "Distance_m",
        "Utilization_pct"
    ]].copy()

    # --- Demand per zone (for bar chart) ---
    zone_demand = (
        assignment_df
        .dropna(subset=["Assigned_Zone"])
        .groupby(["Assigned_Zone","Storage_Type"])["Demand_Lambda_Weekly"]
        .sum()
        .reset_index()
        .rename(columns={"Demand_Lambda_Weekly": "Total_Lambda_in_Zone"})
    )

    # --- Heatmap pivot (Storage_Type x ABC class, Σ λ_j) ---
    heat_data = (
        assignment_df
        .groupby(["Storage_Type","ABC_Class"])["Demand_Lambda_Weekly"]
        .sum()
        .reset_index()
    )
    heat_pivot = heat_data.pivot(
        index="Storage_Type",
        columns="ABC_Class",
        values="Demand_Lambda_Weekly"
    ).fillna(0)

    # --- Expected travel cost Σ λ_j * d_k ---
    assign_with_dist = assignment_df.merge(
        zone_df[["Zone_ID", "Distance_m"]],
        left_on="Assigned_Zone",
        right_on="Zone_ID",
        how="left"
    )

    assign_with_dist["Expected_Travel_Cost"] = (
        assign_with_dist["Demand_Lambda_Weekly"] *
        assign_with_dist["Distance_m"]
    )

    total_travel_cost = float(assign_with_dist["Expected_Travel_Cost"].sum())

    return assignment_df, zone_utilization_df, total_travel_cost, zone_demand, heat_pivot
