let
    Source = RiskHistory,
    KeepColumns = Table.SelectColumns(Source, {"Region", "Feeder", "PoleNumber"}),
    AddAddress = Table.AddColumn(
        KeepColumns,
        "Reseller Address",
        each [Feeder] & " / " & [PoleNumber],
        type text
    ),
    RenamedColumns = Table.RenameColumns(AddAddress, {{"Region", "Reseller Country"}}),
    RemovedColumns = Table.RemoveColumns(RenamedColumns, {"Feeder", "PoleNumber"}),
    DistinctRows = Table.Distinct(RemovedColumns)
in
    DistinctRows
