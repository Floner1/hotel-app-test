-- =====================================================================
-- Widen booking_info.status CHECK constraint to match BOOKING_STATUSES
-- (site1/home/views.py:20-28): adds checked_in, checked_out, rejected.
-- NOT EXECUTED. Review and run manually against the live DB.
-- =====================================================================

-- XACT_ABORT guarantees the whole batch rolls back if any statement fails.
-- Without it a failure between the DROP and the ADD leaves the transaction
-- open and the column unconstrained.
SET XACT_ABORT ON;

BEGIN TRANSACTION;

DECLARE @constraint_name NVARCHAR(128);

SELECT @constraint_name = cc.name
FROM sys.check_constraints cc
JOIN sys.columns col
    ON col.object_id = cc.parent_object_id
   AND col.column_id = cc.parent_column_id
WHERE cc.parent_object_id = OBJECT_ID('booking_info')
  AND col.name = 'status';

IF @constraint_name IS NOT NULL
BEGIN
    DECLARE @drop_sql NVARCHAR(MAX) =
        N'ALTER TABLE booking_info DROP CONSTRAINT ' + QUOTENAME(@constraint_name) + N';';
    EXEC sp_executesql @drop_sql;
END

ALTER TABLE booking_info
    ADD CONSTRAINT chk_booking_status
    CHECK (status IN ('pending','confirmed','checked_in','checked_out','cancelled','completed','rejected'));

COMMIT TRANSACTION;
