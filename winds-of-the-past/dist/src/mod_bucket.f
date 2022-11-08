      MODULE mod_bucket
        CONTAINS

        FUNCTION calculate_bucket(str, num_buckets)
            INTEGER :: calculate_bucket
            INTEGER :: i, bucket
            CHARACTER(len=*),INTENT(IN) :: str
            INTEGER,INTENT(IN) :: num_buckets

            bucket = 0
            DO i = 1, LEN(str)
                bucket = bucket + ICHAR(str(i:i))
            END DO
            calculate_bucket = MOD(bucket, num_buckets)

            RETURN
        END FUNCTION calculate_bucket
      END MODULE mod_bucket
