let
    Source = RiskHistory,
    KeepColumns = Table.SelectColumns(Source, {"Date"}),
    RenamedColumns = Table.RenameColumns(KeepColumns, {{"Date", "End of Month"}}),
    DistinctRows = Table.Distinct(RenamedColumns),
    SortedRows = Table.Sort(DistinctRows, {{"End of Month", Order.Ascending}})
in
    SortedRows
