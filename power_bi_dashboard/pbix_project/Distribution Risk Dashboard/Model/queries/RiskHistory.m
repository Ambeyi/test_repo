let
    Source = Csv.Document(
        File.Contents(DataFilePath),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    ChangedType = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"Date", type date},
            {"Region", type text},
            {"Feeder", type text},
            {"PoleNumber", type text},
            {"AssetID", type text},
            {"EquipmentType", type text},
            {"RiskIndex", type number},
            {"CriticalFlag", Int64.Type},
            {"FailureImpactUSD", Int64.Type}
        }
    )
in
    ChangedType
