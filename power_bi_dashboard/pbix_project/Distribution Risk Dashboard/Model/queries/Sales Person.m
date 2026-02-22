let
    Source = RiskHistory,
    Regions = Table.Distinct(Table.SelectColumns(Source, {"Region"})),
    RenamedColumns = Table.RenameColumns(Regions, {{"Region", "Sales Territory Group"}}),
    AddCountry = Table.AddColumn(RenamedColumns, "Sales Territory Country", each "Taiwan", type text),
    AddSalesPerson = Table.AddColumn(
        AddCountry,
        "Sales Person",
        each if [Sales Territory Group] = "North" then "North Crew"
            else if [Sales Territory Group] = "Central" then "Central Crew"
            else "South Crew",
        type text
    ),
    Reordered = Table.ReorderColumns(AddSalesPerson, {"Sales Person", "Sales Territory Country", "Sales Territory Group"})
in
    Reordered
