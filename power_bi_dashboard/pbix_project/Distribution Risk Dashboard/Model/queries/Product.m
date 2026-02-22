let
    Source = RiskHistory,
    KeepColumns = Table.SelectColumns(Source, {"AssetID", "EquipmentType", "Region", "Feeder"}),
    RenamedColumns = Table.RenameColumns(
        KeepColumns,
        {
            {"EquipmentType", "Category"},
            {"AssetID", "Model"},
            {"Region", "Color"},
            {"Feeder", "SubCategory"}
        }
    ),
    AddNumber = Table.AddColumn(RenamedColumns, "Number", each [Model], type text),
    AddThumbnail = Table.AddColumn(
        AddNumber,
        "Thumbnail",
        each "https://dummyimage.com/1x1/ffffff/ffffff.png",
        type text
    ),
    DistinctRows = Table.Distinct(AddThumbnail)
in
    DistinctRows
