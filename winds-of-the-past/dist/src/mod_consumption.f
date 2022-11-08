      MODULE mod_consumption
        USE mod_turbine

        ABSTRACT INTERFACE
              SUBROUTINE abstract_pretty_print(ev_guess,k)
                INTEGER :: k
                DOUBLE PRECISION :: ev_guess(k)
                INTEGER :: counter
              END SUBROUTINE abstract_pretty_print
       END INTERFACE
        CONTAINS

        SUBROUTINE pretty_print(vector,k)
              INTEGER :: k
              DOUBLE PRECISION :: vector(k)
              INTEGER :: counter
              
              WRITE (*,*) "----------------------------------------"
              DO counter = 1, k
                WRITE(*,"(I10,A)",ADVANCE="NO") counter, ": "
                WRITE(*,*) vector(k)
              END DO
              WRITE (*,*) "----------------------------------------"
        END SUBROUTINE pretty_print
                
        FUNCTION total_capacity_for_turbines(average_wind_velocity,
     c      turbine_ids,turbine_checksums)
            USE mod_bucket
            USE mod_turbine

            REAL,INTENT(IN) :: average_wind_velocity
            CHARACTER(len=36),INTENT(IN)  :: turbine_ids(10)
            CHARACTER(len=128),INTENT(IN) :: turbine_checksums(10)
            RECORD /TURBINE/ turbine
            INTEGER :: bucket, ios
            CHARACTER(len=128) :: turbine_username
            CHARACTER(len=3) :: bucket_str
            ! 1.225 kg/m**3
            REAL :: air_density=1.225
            REAL :: swep_area
            REAL :: total_capacity_for_turbines
            CHARACTER(LEN=512) :: path
            INTEGER :: logged_in, i
            CHARACTER(len=128) :: logged_in_username
            RECORD /MODELDETAILS/ modeldetails(5)
            COMMON /session_status/ logged_in, logged_in_username
            COMMON /model_details/ modeldetails

            total_capacity_for_turbines = 0.0

            DO i = 1,10
              bucket = calculate_bucket(turbine_ids(i),
     c                                  NUM_TURBINE_BUCKETS)
              WRITE(bucket_str,"(I0.3)") bucket

              path = "data/turbines/"
     c               // bucket_str // "/"
     c               // TRIM(turbine_ids(i)) // ".DAT"
              OPEN(9,FILE=path,
     c                   ACTION="READ",IOSTAT=ios)
                    DO
                        READ(9,"(2A,I1,2A)",IOSTAT=ios) turbine%id,
     c                                  turbine%description,
     c                                  turbine%modelnumber,
     c                                  turbine%checksum,
     c                                  turbine_username
                        IF(ios .NE. 0) THEN
                            EXIT
                        END IF

                        IF(turbine_checksums(i) .EQ.
     c                    turbine%checksum) THEN
                            !Calculate the power after the formula
                            WRITE (*,*) turbine%checksum
                            swep_area =
     c                          modeldetails(turbine%modelnumber)
     c                       %swep_area
                            WRITE (*,*) swep_area
                            total_capacity_for_turbines =
     c                       total_capacity_for_turbines
     c                       + 0.5 * (swep_area * air_density *
     c                       average_wind_velocity**3)
                        END IF

                    END DO
                    CLOSE(9)
                END DO
        END FUNCTION total_capacity_for_turbines

        SUBROUTINE read_initial_vector(ev_guess,k)
              INTEGER :: k
              INTEGER :: counter
              DOUBLE PRECISION :: ev_guess(k)
              
              WRITE (*,"(A)") "Enter the initial guess vector:"
              DO counter = 1, k
                WRITE(*,"(I10,A)",ADVANCE="NO") counter, ": "
                READ(*,*) ev_guess(counter:counter)
              END DO
        END SUBROUTINE read_initial_vector
        
        FUNCTION approx_max_ev(usage_arr,n)
          DOUBLE PRECISION,INTENT(IN) :: usage_arr(n,n)
          INTEGER,INTENT(IN) :: n
          PROCEDURE(abstract_pretty_print), POINTER :: p1
          INTEGER :: max_iterations = 300
          INTEGER :: k=3
          INTEGER :: idx_max_val
          DOUBLE PRECISION :: tolerance_eps = 0.001
          DOUBLE PRECISION :: max_ev
          DOUBLE PRECISION :: ev_guess(3)
          DOUBLE PRECISION :: ev_guess_normalized(n)
          DOUBLE PRECISION :: intermediate_vec(n)
          DOUBLE PRECISION :: max_val
          DOUBLE PRECISION :: approx_max_ev
          p1 => pretty_print


          CALL read_initial_vector(ev_guess,k)
          CALL p1(ev_guess,n)
          
          DO idx_max_val=1,n
            IF(ABS(ev_guess(idx_max_val)) .EQ. MAXVAL(ABS(ev_guess)))
     c          THEN
                EXIT
            END IF
          END DO

          DO k=1,max_iterations
            intermediate_vec=MATMUL(usage_arr,ev_guess)
            max_ev=intermediate_vec(idx_max_val)

            DO idx_max_val=1,n
                IF(ABS(intermediate_vec(idx_max_val)) .EQ.
     c           MAXVAL(ABS(intermediate_vec))) EXIT
            END DO

            ev_guess_normalized=intermediate_vec/
     c      intermediate_vec(idx_max_val)
            max_val=MAXVAL(ABS(ev_guess-ev_guess_normalized))
            ev_guess=ev_guess_normalized

            IF(max_val < tolerance_eps) THEN
                WRITE(*,"(A14,I10,A)") "Stopped after:",k,
     c           " iterations"           
                approx_max_ev = max_ev
                RETURN
            END IF

          END DO
        END FUNCTION approx_max_ev

        SUBROUTINE read_array(usage_arr,n)
            DOUBLE PRECISION,INTENT(INOUT) :: usage_arr(n,n)
            INTEGER,INTENT(IN) :: n
            INTEGER :: row_ctr

            WRITE(*,"(A)") "Enter consumption array per household:"

            DO row_ctr = 1, n
                WRITE(*,"(I10,A)",ADVANCE="NO") row_ctr, ": "
                READ(*,*) usage_arr(row_ctr,:)
            END DO
        END SUBROUTINE read_array

        FUNCTION max_household_consumption_day(usage_arr,n)
            DOUBLE PRECISION :: max_household_consumption_day
            DOUBLE PRECISION,INTENT(INOUT) :: usage_arr(n,n)
            INTEGER :: n
            DOUBLE PRECISION :: max_eigenvalue,avg_consumption

            CALL read_array(usage_arr,n)
            max_household_consumption_day =
     c      MAXVAL(RESHAPE(usage_arr,(/n*n/)))
            avg_consumption = SUM(usage_arr) / n

            !calculate eigenvectors using power method or so...
            max_eigenvalue = approx_max_ev(usage_arr,n)
            WRITE(*,"(A,F10.4)") "Max consumption: ",
     c                           max_household_consumption_day
            WRITE(*,"(A,F10.4)") "Average consumption: ",avg_consumption
            WRITE(*,"(A,F10.4)") "Max Eigenvalue is: ",max_eigenvalue

        END FUNCTION max_household_consumption_day


        SUBROUTINE calculate_turbine_capacity()
            REAL :: average_wind_velocity
            DOUBLE PRECISION :: household_usage_arr(3,3)
            DOUBLE PRECISION :: max_capacity
            DOUBLE PRECISION :: total_household_consumption
            DOUBLE PRECISION :: max_household_consumption
            INTEGER :: n = 3
            INTEGER :: counter
            CHARACTER(len=128) :: turbine_checksums(10)
            CHARACTER(len=36) :: turbine_ids(10)
            INTEGER :: number_of_turbines
            counter = 1

            WRITE(*,"(A)",ADVANCE="NO") "Average Wind Velocity: "
            READ(*,"(F30.20)") average_wind_velocity

            WRITE(*,"(A)",ADVANCE="NO") "Enter the number of the "//
     c                              "turbines to calculate: "
            READ(*,"(I2)") number_of_turbines

            IF(number_of_turbines .GT.
     c          MAX_HOUSEHOLD_CONSUMPTION_TURBINES .OR.
     c          number_of_turbines .LT. 0) THEN
                number_of_turbines = MAX_HOUSEHOLD_CONSUMPTION_TURBINES
            END IF

            WRITE(*,"(A)") "Enter the IDs of the "//
     c                       "turbines to calculate: "

            ! Read in turbine check sums
            DO WHILE(counter .LT. number_of_turbines + 1)
                WRITE(*,"(I10,A)",ADVANCE="NO") counter, ": "
                READ(*,"(A)") turbine_ids(counter)
                counter = counter + 1
            END DO

            counter = 1
            WRITE(*,"(A)") "Enter the checksums of the "//
     c                       "turbines to calculate: "
            DO WHILE(counter .LT. number_of_turbines + 1)
              WRITE(*,"(I10,A)",ADVANCE="NO") counter, ": "
              READ(*,"(A)") turbine_checksums(counter)
              counter = counter + 1
            END DO

            ! Read in user data in the format
            ! H1, H2, H3
            ! Consumption Day 1, Consumption Day 1, Consumption Day 1
            ! Consumption Day 2, Consumption Day 2, Consumption Day 2
            max_household_consumption =
     c       max_household_consumption_day(household_usage_arr,n)
            max_capacity =
     c      total_capacity_for_turbines(average_wind_velocity,
     c      turbine_ids,turbine_checksums)

            total_household_consumption = SUM(household_usage_arr)

            IF (max_capacity > max_household_consumption) THEN
              WRITE(*,"(A)") "Good job! "//
     c         "Your turbines can manage the power consumption"//
     c         "of the provided households."
            ELSE
              WRITE(*,"(A)") "Oh noze :( "//
     c         "Please upgrade your power network!!!"
            END IF
            WRITE(*,"(A,F10.4)") "Maximum capacity: ", max_capacity
            WRITE(*,"(A,F10.4)") "Total household consumption: ",
     c                       total_household_consumption

        END SUBROUTINE calculate_turbine_capacity
      END MODULE mod_consumption
