let
    Source = RiskHistory,
    KeepColumns = Table.SelectColumns(
        Source,
        {"Date", "AssetID", "RiskIndex", "CriticalFlag", "FailureImpactUSD", "Region", "Feeder", "PoleNumber"}
    ),
    AddResellerAddress = Table.AddColumn(
        KeepColumns,
        "Reseller Address",
        each [Feeder] & " / " & [PoleNumber],
        type text
    ),
    RenamedColumns = Table.RenameColumns(
        AddResellerAddress,
        {
            {"Date", "End of Month"},
            {"AssetID", "Product Number"},
            {"RiskIndex", "Sales Amount"},
            {"CriticalFlag", "Sales Order Qty"},
            {"FailureImpactUSD", "Failure Impact"},
            {"Region", "Sales Territory Group"}
        }
    ),
    RemovedColumns = Table.RemoveColumns(RenamedColumns, {"Feeder", "PoleNumber"}),
    ChangedType = Table.TransformColumnTypes(
        RemovedColumns,
        {
            {"End of Month", type date},
            {"Product Number", type text},
            {"Sales Amount", type number},
            {"Sales Order Qty", Int64.Type},
            {"Failure Impact", Int64.Type},
            {"Sales Territory Group", type text},
            {"Reseller Address", type text}
        }
    )
in
    ChangedType
