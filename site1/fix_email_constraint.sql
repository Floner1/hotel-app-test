-- First, find the constraint name
SELECT CONSTRAINT_NAME
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
WHERE TABLE_NAME = 'booking_info'
  AND CONSTRAINT_TYPE = 'UNIQUE';

-- Drop the UNIQUE constraint on email (replace UQ_ConstraintName with actual name from above)
-- You'll need to run this after seeing the constraint name:
-- ALTER TABLE booking_info DROP CONSTRAINT UQ_ConstraintName;
