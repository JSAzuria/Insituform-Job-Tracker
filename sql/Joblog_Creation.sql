USE [EDW]
GO

/****** Object:  View [dbo].[vw_Dim_JOBLOG_Creation]    Script Date: 6/11/2026 11:42:24 AM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE VIEW [dbo].[vw_Dim_JOBLOG_Creation]
AS

WITH CleanSalesOrder AS
(
    SELECT *
    FROM [EDW].[dbo].[Dim_Sales_Order]
    WHERE NULLIF(LTRIM(RTRIM(UPPER(Order_Number))), 'UNKNOWN') IS NOT NULL
),

PalletFlags AS
(
    SELECT
        dso.Lot_Serial_Number,

        MAX(CASE WHEN LEFT(LTRIM(RTRIM(di.Second_Item_Number)),3) = '370' THEN 1 ELSE 0 END) AS HasME,
        MAX(CASE WHEN LEFT(LTRIM(RTRIM(di.Second_Item_Number)),3) = '390' THEN 1 ELSE 0 END) AS HasSR,

        MAX(
            CASE
                WHEN dw.Description LIKE '%FLAT PLATE SAMPLE%'
                  OR dw.Description LIKE '%FLAT PLATE SAMPLES%'
                THEN COALESCE(
                        TRY_CONVERT(INT,
                            CASE
                                WHEN CHARINDEX('(', dw.Description) > 0
                                 AND CHARINDEX(')', dw.Description) > CHARINDEX('(', dw.Description)
                                THEN SUBSTRING(
                                        dw.Description,
                                        CHARINDEX('(', dw.Description) + 1,
                                        CHARINDEX(')', dw.Description) - CHARINDEX('(', dw.Description) - 1
                                     )
                                ELSE '1'
                            END
                        ), 1
                     )
                ELSE 0
            END
        ) AS FPSCount,

        MAX(CASE WHEN dw.Description LIKE '%RUSH%' THEN 1 ELSE 0 END) AS HasRUSH
    FROM CleanSalesOrder dso
    LEFT JOIN [EDW].[dbo].[Fact_Sales_Order] fso
        ON fso.PK_DIM_SALES_ORDER = dso.PK_DIM_SALES_ORDER
    LEFT JOIN [EDW].[dbo].[Dim_Item] di
        ON fso.PK_Dim_Item = di.PK_Dim_Item
    LEFT JOIN [EDW].[dbo].[Dim_Work_Order_Master] dw
        ON dw.Lot_Serial_Number = dso.Lot_Serial_Number
    WHERE NULLIF(LTRIM(RTRIM(dso.Lot_Serial_Number)), '') IS NOT NULL
    GROUP BY dso.Lot_Serial_Number
),

PullBeltFlags AS
(
    SELECT
        dso.Order_Number,
        dso.Order_Type,
        dso.Reporting_Company,
        dso.Lot_Serial_Number,

        MAX(
            CASE
                WHEN ISNULL(TRY_CONVERT(int, dso.Status_Code_Next), -1) <> 999
                  AND (
                        dso.Item_Number_Short = 17689
                        OR LTRIM(RTRIM(dso.Item_Number_2)) = '3600021'
                        OR LTRIM(RTRIM(dso.Item_Number_3)) = '3600021'
                        OR dso.Description LIKE '%PULL BELT%'
                  )
                THEN 1 ELSE 0
            END
        ) AS HasPullBelt
    FROM CleanSalesOrder dso
    WHERE NULLIF(LTRIM(RTRIM(dso.Lot_Serial_Number)), '') IS NOT NULL
    GROUP BY
        dso.Order_Number,
        dso.Order_Type,
        dso.Reporting_Company,
        dso.Lot_Serial_Number
),

JobLevel AS
(
    SELECT
        dw.Order_Number AS JobNumber,
        MAX(di.Item_Diameter) AS Diameter,
        MAX(di.Item_Thickness) AS Thickness,
        MAX(fso.Quantity_Ordered) AS Length,
        MAX(dc.Customer_Name) AS Customer,
        MIN(
            CONVERT(
                date,
                DATEADD(
                    DAY,
                    (dso.SDPPDJ_Promised_Ship_Date % 1000) - 1,
                    DATEFROMPARTS(
                        CASE
                            WHEN (dso.SDPPDJ_Promised_Ship_Date / 100000) = 0
                                THEN 1900 + ((dso.SDPPDJ_Promised_Ship_Date / 1000) % 100)
                            ELSE 2000 + ((dso.SDPPDJ_Promised_Ship_Date / 1000) % 100)
                        END,
                        1,
                        1
                    )
                )
            )
        ) AS ShipBy
    FROM [EDW].[dbo].[Fact_Work_Order_Master] fw
    LEFT JOIN [EDW].[dbo].[Dim_Work_Order_Master] dw
        ON fw.PK_Dim_Work_Order_Master = dw.PK_Dim_Work_Order_Master
        AND dw.Business_Unit = 'BATESVILLE'
        AND dw.Date_Order_Transaction >= '2026-01-01'
    LEFT JOIN CleanSalesOrder dso
        ON TRY_CONVERT(BIGINT, dw.Related_PO_Number) = TRY_CONVERT(BIGINT, dso.Order_Number)
        AND TRY_CONVERT(DECIMAL(10,2), dw.Line_Number) = TRY_CONVERT(DECIMAL(10,2), dso.Order_Line_Number)
        AND dw.Related_Order_Type = dso.Order_Type
        AND dw.Company = dso.Reporting_Company
    LEFT JOIN [EDW].[dbo].[Fact_Sales_Order] fso
        ON fso.PK_DIM_SALES_ORDER = dso.PK_DIM_SALES_ORDER
    LEFT JOIN [EDW].[dbo].[Dim_Item] di
        ON fso.PK_Dim_Item = di.PK_Dim_Item
    LEFT JOIN [EDW].[dbo].[Dim_Customer] dc
        ON fso.PK_DIM_CUSTOMER = dc.PK_Dim_Customer
    GROUP BY dw.Order_Number
),

CleanItemNumber AS
(
    SELECT
        PK_Dim_Work_Order_Master,
        CASE
            WHEN PATINDEX('%[^0-9]', REVERSE(LTRIM(RTRIM(Second_Item_Number)))) = 0
                THEN LTRIM(RTRIM(Second_Item_Number))
            ELSE LEFT(
                    LTRIM(RTRIM(Second_Item_Number)),
                    LEN(LTRIM(RTRIM(Second_Item_Number)))
                    - PATINDEX('%[0-9]%', REVERSE(LTRIM(RTRIM(Second_Item_Number))))
                    + 1
                 )
        END AS Second_Item_Number_Clean
    FROM [EDW].[dbo].[Dim_Work_Order_Master]
    WHERE Business_Unit = 'BATESVILLE'
      AND Date_Order_Transaction >= '2026-01-01'
),

NoPO_Length AS
(
    SELECT
        di_sub.Second_Item_Number,
        MAX(fso_sub.Quantity_Ordered) AS Length
    FROM [EDW].[dbo].[Fact_Sales_Order] fso_sub
    JOIN [EDW].[dbo].[Dim_Item] di_sub
        ON fso_sub.PK_Dim_Item = di_sub.PK_Dim_Item
    WHERE di_sub.Second_Item_Number IS NOT NULL
    GROUP BY di_sub.Second_Item_Number
),

DescFlags AS
(
    SELECT
        PK_DIM_SALES_ORDER,
        CASE WHEN Description LIKE '%LFP%' THEN 1 ELSE 0 END AS f_LFP,
        CASE WHEN Description LIKE '%PU%' THEN 1 ELSE 0 END AS f_PU,
        CASE WHEN Description LIKE '%RT%' THEN 1 ELSE 0 END AS f_RT,
        CASE WHEN Description LIKE '%PIP%' THEN 1 ELSE 0 END AS f_PIP,
        CASE WHEN Description LIKE '%SBL%' THEN 1 ELSE 0 END AS f_SBL,
        CASE WHEN Description LIKE '%PULLIN%' THEN 1 ELSE 0 END AS f_PULLIN,
        CASE WHEN Description LIKE '%IMN%' THEN 1 ELSE 0 END AS f_IMN,
        CASE WHEN Description LIKE '%DT%' THEN 1 ELSE 0 END AS f_DT,
        CASE WHEN Description LIKE '%ICP%' THEN 1 ELSE 0 END AS f_ICP,
        CASE WHEN Description LIKE '%EXP%' THEN 1 ELSE 0 END AS f_EXP,
        CASE WHEN Description LIKE '%ILS%' THEN 1 ELSE 0 END AS f_ILS,
        CASE WHEN Description LIKE '%UP%' THEN 1 ELSE 0 END AS f_UP,
        CASE WHEN Description LIKE '%RPP%' THEN 1 ELSE 0 END AS f_RPP
    FROM [EDW].[dbo].[Dim_Sales_Order]
    WHERE NULLIF(LTRIM(RTRIM(UPPER(Order_Number))), 'UNKNOWN') IS NOT NULL
),

SerialDesc AS
(
    SELECT SerialNumber, ItemDesc
    FROM (VALUES
        (2631221, 'EXT'),
        (2630221, 'EXT')
    ) AS t(SerialNumber, ItemDesc)
)

SELECT
    dw.Order_Number AS JobNumber,
    dso.Order_Number AS [ST-SO Number],
    dso.Description_2,
    dso.Lot_Serial_Number AS PalletNumber,

    CASE
        WHEN CHARINDEX('.', CAST(dw.Line_Number AS VARCHAR(20))) > 0 
             AND EXISTS (
                 SELECT 1
                 FROM [EDW].[dbo].[Fact_Work_Order_Master] fw_sub
                 JOIN [EDW].[dbo].[Dim_Work_Order_Master] dw_sub
                    ON fw_sub.PK_Dim_Work_Order_Master = dw_sub.PK_Dim_Work_Order_Master
                 JOIN CleanSalesOrder dso_sub
                    ON TRY_CONVERT(BIGINT, dw_sub.Related_PO_Number) = TRY_CONVERT(BIGINT, dso_sub.Order_Number)
                    AND TRY_CONVERT(DECIMAL(10,2), dw_sub.Line_Number) = TRY_CONVERT(DECIMAL(10,2), dso_sub.Order_Line_Number)
                    AND dw_sub.Related_Order_Type = dso_sub.Order_Type
                    AND dw_sub.Company = dso_sub.Reporting_Company
                 WHERE dso_sub.Lot_Serial_Number = dso.Lot_Serial_Number
                   AND dw_sub.Line_Number = SUBSTRING(CAST(dw.Line_Number AS VARCHAR(20)), 1, CHARINDEX('.', CAST(dw.Line_Number AS VARCHAR(20))) - 1)
                   AND UPPER(dw_sub.Description) NOT LIKE '%STARTER%'
                   AND UPPER(dw_sub.Description) NOT LIKE '%RUSH%'
                   AND UPPER(dw_sub.Description) NOT LIKE '%ME%'
                   AND UPPER(dw_sub.Description) NOT LIKE '%PLATE SAMPLE%'
             ) THEN 'NEW'

        WHEN CHARINDEX('.', CAST(dw.Line_Number AS VARCHAR(20))) = 0
             AND EXISTS (
                 SELECT 1
                 FROM [EDW].[dbo].[Fact_Work_Order_Master] fw_sub
                 JOIN [EDW].[dbo].[Dim_Work_Order_Master] dw_sub
                    ON fw_sub.PK_Dim_Work_Order_Master = dw_sub.PK_Dim_Work_Order_Master
                 JOIN CleanSalesOrder dso_sub
                    ON TRY_CONVERT(BIGINT, dw_sub.Related_PO_Number) = TRY_CONVERT(BIGINT, dso_sub.Order_Number)
                    AND TRY_CONVERT(DECIMAL(10,2), dw_sub.Line_Number) = TRY_CONVERT(DECIMAL(10,2), dso_sub.Order_Line_Number)
                    AND dw_sub.Related_Order_Type = dso_sub.Order_Type
                    AND dw_sub.Company = dso_sub.Reporting_Company
                 WHERE dso_sub.Lot_Serial_Number = dso.Lot_Serial_Number
                   AND CAST(dw_sub.Line_Number AS VARCHAR(20)) LIKE CAST(dw.Line_Number AS VARCHAR(20)) + '.%'
                   AND UPPER(dw_sub.Description) NOT LIKE '%STARTER%'
                   AND UPPER(dw_sub.Description) NOT LIKE '%RUSH%'
                   AND UPPER(dw_sub.Description) NOT LIKE '%ME%'
                   AND UPPER(dw_sub.Description) NOT LIKE '%PLATE SAMPLE%'
             ) THEN 'OLD'
        ELSE NULL
    END AS Revision,

    jl.Customer,
    dw.Description AS WorkOrder_Description,

    CASE
        WHEN dw.Description LIKE '%Tran%'
            THEN 'TRANSITION TO:'
        WHEN dw.Description LIKE '%TAP%'
            THEN CONCAT(
                    'TAPER (OVER ',
                    CAST(jl.Length AS varchar(20)),
                    ''' @ ',
                    COALESCE(CAST(TRY_CONVERT(FLOAT, jl.Thickness) AS varchar(20)), CAST(jl.Thickness AS varchar(20))),
                    'MM)'
                 )
        ELSE COALESCE(CAST(TRY_CONVERT(FLOAT, ca_calc.RawDia) AS varchar(50)), ca_calc.RawDia)
    END AS Diameter,

    CASE
        WHEN dw.Description LIKE '%Tran%' THEN NULL
        WHEN dw.Description LIKE '%TAP%' THEN NULL
        ELSE COALESCE(CAST(TRY_CONVERT(FLOAT, ca_calc.RawThick) AS varchar(50)), ca_calc.RawThick)
    END AS Thickness,

    CASE
        WHEN dw.Description LIKE '%Tran%' THEN NULL
        WHEN NULLIF(LTRIM(RTRIM(dw.Related_PO_Number)), '') IS NULL
            THEN npl.Length
        ELSE jl.Length
    END AS Length,

    dw.Date_Order_Transaction AS OrderDate,
    jl.ShipBy,
    dw.Date_Completed,

    CASE
        WHEN pf.HasME = 0
         AND pf.HasSR = 0
         AND pf.FPSCount = 0
         AND ISNULL(pb.HasPullBelt, 0) = 0
            THEN NULL
        ELSE CONCAT(
            CASE WHEN pf.HasME = 1 THEN 'ME' ELSE '' END,
            CASE WHEN pf.HasSR = 1 THEN 'SR' ELSE '' END,
            CASE WHEN pf.FPSCount > 0 THEN CONCAT('FPS(', pf.FPSCount, ')') ELSE '' END,
            CASE WHEN ISNULL(pb.HasPullBelt, 0) = 1 THEN 'PB' ELSE '' END
        )
    END AS SP_APP,

    CASE WHEN ISNULL(pb.HasPullBelt, 0) = 1 THEN 'Y' ELSE 'N' END AS PullBelt,
    CASE WHEN pf.HasRUSH = 1 THEN 'Y' ELSE 'N' END AS RUSH,

    CASE
        WHEN dw.Description LIKE '%Plate%'
          OR dw.Description LIKE '%Connector%'
          OR dw.Description LIKE '%Additional%'
          OR dw.Description LIKE '%Starter%'
          OR dw.Description LIKE '%charge%'
        THEN NULL
        ELSE
        (
            SELECT STRING_AGG(val, '/')
            FROM (
                SELECT 'EXT' AS val WHERE UPPER(dw.Description) LIKE '%LFP%'
                UNION SELECT 'PU' WHERE df.f_PU = 1
                UNION SELECT 'RT' WHERE df.f_RT = 1
                UNION SELECT 'PIP' WHERE df.f_PIP = 1
                UNION SELECT 'SBL' WHERE df.f_SBL = 1
                UNION SELECT 'PIP' WHERE df.f_PULLIN = 1
                UNION SELECT 'IMAIN' WHERE df.f_IMN = 1
                UNION SELECT 'DT' WHERE df.f_DT = 1
                UNION SELECT 'ICP' WHERE df.f_ICP = 1
                UNION SELECT 'EXP' WHERE df.f_EXP = 1
                UNION SELECT 'ILS' WHERE df.f_ILS = 1
                UNION SELECT 'Ultra Pipe' WHERE df.f_UP = 1
                UNION SELECT 'RPP' WHERE df.f_RPP = 1
                UNION SELECT 'FLEXSEAM' WHERE LOWER(dw.Description) LIKE '%flex%'
                UNION SELECT 'AIRTEST' WHERE LOWER(dw.Description) LIKE '%air%'
                UNION SELECT 'METERS' WHERE LOWER(jl.Customer) LIKE '%canada west%'
                UNION SELECT sd.ItemDesc WHERE sd.ItemDesc IS NOT NULL
                UNION SELECT 'END ON TOP' WHERE LOWER(dso.Description_2) LIKE '%top%' AND LOWER(dso.Description_2) NOT LIKE '%me top of stack%'
                UNION SELECT 'END ON BOTTOM' WHERE LOWER(dso.Description_2) LIKE '%bottom%' AND LOWER(dso.Description_2) NOT LIKE '%me bottom of stack%'
                UNION SELECT 'METERS' WHERE LOWER(dso.Description_2) LIKE '%meter%'
                UNION SELECT 'FLEXSEAM' WHERE LOWER(dso.Description_2) LIKE '%taped seams%' AND LOWER(dso.Description_2) NOT LIKE '%meter%'
                UNION SELECT 'UltraPipe' WHERE LOWER(dso.Description_2) LIKE '%ultra pipe%' OR LTRIM(RTRIM(UPPER(dso.Description_2))) = 'UP'
                UNION SELECT 'DOT' WHERE LOWER(dso.Description_2) LIKE '%dot shot%'
                UNION SELECT 'OTH' WHERE LOWER(dso.Description_2) LIKE '%oth%'
                UNION SELECT 'NO MARKINGS' WHERE LOWER(dso.Description_2) LIKE '%do not mark%' OR LOWER(dso.Description_2) LIKE '%no markings%' OR LOWER(dso.Description_2) LIKE '%no print%'
                UNION SELECT 'DRINKING WATER' WHERE LOWER(dso.Description_2) LIKE '%drinking water%'
                UNION SELECT 'NO REPAIRS' WHERE LOWER(dso.Description_2) LIKE '%no repiars%'
                UNION SELECT 'print w-"mtc pip"' WHERE LOWER(dso.Description_2) LIKE '%mtc pip%'
                UNION SELECT 'print w-"mtc imain"' WHERE LOWER(dso.Description_2) LIKE '%mtc imain%'
                UNION SELECT 'print w-"mtc iplus"' WHERE LOWER(dso.Description_2) LIKE '%mtc iplus%'
                UNION SELECT 'print w-"mtube pip"' WHERE LOWER(dso.Description_2) LIKE '%mtube pip%'
                UNION SELECT 'print w-"mtube"' WHERE LOWER(dso.Description_2) LIKE '%mtube%' AND LOWER(dso.Description_2) NOT LIKE '%mtube pip%'
                UNION SELECT 'print w-"yard marks only"' WHERE LOWER(dso.Description_2) LIKE '%yard marks only%'
                UNION SELECT 'PU' WHERE LTRIM(RTRIM(UPPER(dso.Description_2))) = 'PU'
                UNION SELECT 'TRIAL' WHERE LOWER(dso.Description_2) LIKE '%trial%'
                UNION SELECT 'AIRTEST' WHERE LOWER(dso.Description_2) LIKE '%air%test%' OR LOWER(dso.Description_2) LIKE '%airtest%'
                UNION SELECT 'STENCIL REQUIRED' WHERE LOWER(dso.Description_2) LIKE '%stencil%req%' OR LOWER(dso.Description_2) LIKE '%stencil required%' OR LOWER(dso.Description_2) LIKE '%stencil reuqired%'
                UNION SELECT 'ME on Top' WHERE LOWER(dso.Description_2) LIKE '%me top of stack%'
                UNION SELECT 'ME on Bottom' WHERE LOWER(dso.Description_2) LIKE '%me bottom of stack%'
                UNION SELECT 'STENCIL - T/R END' WHERE LOWER(dso.Description_2) LIKE '%stencil - t/r end%'
                UNION SELECT 'STENCIL ME END' WHERE LOWER(dso.Description_2) LIKE '%stencil me end%'
                UNION SELECT 'T/R - STENCIL REQUIRED' WHERE LOWER(dso.Description_2) LIKE '%t/r - stencil req%'
                UNION SELECT dso.Description_2 WHERE LOWER(dso.Description_2) LIKE '%sample%' OR LOWER(dso.Description_2) LIKE '%fps required%' OR LOWER(dso.Description_2) LIKE '%up1900%'
            ) AS x
        )
    END AS [DESC]

FROM [EDW].[dbo].[Fact_Work_Order_Master] fw

LEFT JOIN [EDW].[dbo].[Dim_Work_Order_Master] dw
    ON fw.PK_Dim_Work_Order_Master = dw.PK_Dim_Work_Order_Master

LEFT JOIN CleanSalesOrder dso
    ON TRY_CONVERT(BIGINT, dw.Related_PO_Number) = TRY_CONVERT(BIGINT, dso.Order_Number)
    AND TRY_CONVERT(DECIMAL(10,2), dw.Line_Number) = TRY_CONVERT(DECIMAL(10,2), dso.Order_Line_Number)
    AND dw.Related_Order_Type = dso.Order_Type
    AND dw.Company = dso.Reporting_Company

LEFT JOIN [EDW].[dbo].[Fact_Sales_Order] fso
    ON fso.PK_DIM_SALES_ORDER = dso.PK_DIM_SALES_ORDER

LEFT JOIN [EDW].[dbo].[Dim_Item] di
    ON fso.PK_Dim_Item = di.PK_Dim_Item

LEFT JOIN PalletFlags pf
    ON pf.Lot_Serial_Number = dso.Lot_Serial_Number

LEFT JOIN PullBeltFlags pb
    ON pb.Order_Number = dso.Order_Number
    AND pb.Order_Type = dso.Order_Type
    AND pb.Reporting_Company = dso.Reporting_Company
    AND pb.Lot_Serial_Number = dso.Lot_Serial_Number

LEFT JOIN JobLevel jl
    ON jl.JobNumber = dw.Order_Number

LEFT JOIN CleanItemNumber cin
    ON cin.PK_Dim_Work_Order_Master = dw.PK_Dim_Work_Order_Master

LEFT JOIN NoPO_Length npl
    ON npl.Second_Item_Number = cin.Second_Item_Number_Clean

LEFT JOIN SerialDesc sd
    ON TRY_CONVERT(BIGINT, cin.Second_Item_Number_Clean) = sd.SerialNumber

LEFT JOIN DescFlags df
    ON df.PK_DIM_SALES_ORDER = dso.PK_DIM_SALES_ORDER

CROSS APPLY
(
    SELECT
        CASE
            WHEN PATINDEX('%[0-9]"%', dw.Description) > 0
            THEN SUBSTRING(
                    dw.Description,
                    PATINDEX('%[0-9]"%', dw.Description)
                    - PATINDEX(
                        '%[^0-9.]%',
                        REVERSE(LEFT(dw.Description, PATINDEX('%[0-9]"%', dw.Description) - 1))
                    ) + 1,
                    PATINDEX(
                        '%[^0-9.]%',
                        REVERSE(LEFT(dw.Description, PATINDEX('%[0-9]"%', dw.Description) - 1))
                    )
                 )
            ELSE CAST(jl.Diameter AS varchar(50))
        END AS RawDia,

        CASE
            WHEN PATINDEX('%x [0-9]%[0-9]MM%', dw.Description) > 0
            THEN SUBSTRING(
                    dw.Description,
                    PATINDEX('%x [0-9]%', dw.Description) + 2,
                    PATINDEX(
                        '%MM%',
                        SUBSTRING(
                            dw.Description,
                            PATINDEX('%x [0-9]%', dw.Description) + 2,
                            LEN(dw.Description)
                        )
                    ) - 1
                 )
            ELSE CAST(jl.Thickness AS varchar(50))
        END AS RawThick
) AS ca_calc

WHERE dw.Business_Unit = 'BATESVILLE'
  AND dw.Date_Order_Transaction >= '2026-01-01'
  AND (
        NULLIF(LTRIM(RTRIM(dw.Related_PO_Number)), '') IS NULL
        OR (
             jl.ShipBy IS NOT NULL
             AND UPPER(dw.Description) NOT LIKE '%PLATE%'
             AND UPPER(dw.Description) NOT LIKE '%CONNECTOR%'
             AND UPPER(dw.Description) NOT LIKE '%ADDITIONAL%'
             AND UPPER(dw.Description) NOT LIKE '%STARTER%'
             AND UPPER(dw.Description) NOT LIKE '%CHARGE%'
             AND UPPER(dw.Description) NOT LIKE '%ZIA%'
             AND UPPER(dw.Description) NOT LIKE '%SHORT%'
             AND UPPER(dw.Description) NOT LIKE '%RUSH%'
             AND UPPER(dw.Description) NOT LIKE '%ME%'
           )
      )
GO


