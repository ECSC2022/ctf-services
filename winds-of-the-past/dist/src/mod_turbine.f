      MODULE MOD_TURBINE
          USE mod_crypto

          INTEGER :: MAX_HOUSEHOLD_CONSUMPTION_TURBINES = 10
          INTEGER :: NUM_TURBINE_BUCKETS = 256
          INTEGER :: NUM_TURBINE_REGISTRATION_TRIES = 3


          STRUCTURE /TURBINE/
              CHARACTER(len=36) id
              CHARACTER(len=128) checksum
              CHARACTER(len=512) description
              INTEGER modelnumber
          END STRUCTURE

          STRUCTURE /MODELDETAILS/
              INTEGER modelnumber
              CHARACTER(len=512) name
              REAL swep_area
          END STRUCTURE

          

          CONTAINS

          SUBROUTINE show_turbine_details()
              USE mod_bucket

              RECORD /TURBINE/ turbine
              INTEGER :: logged_in, bucket, ios
              CHARACTER(len=512) :: path
              CHARACTER(len=128) :: logged_in_username,
     c                              turbine_checksum
              CHARACTER(len=36) :: turbine_id
     c                              
              RECORD /MODELDETAILS/ modeldetails(5)
              CHARACTER(len=3) :: bucket_str
                
              COMMON /session_status/ logged_in, logged_in_username
              COMMON /model_details/ modeldetails
              
              WRITE(*,"(A)",ADVANCE="NO") "Enter the ID of the "//
     c                       "turbine to display: "
              READ(*,"(A)") turbine_id

              WRITE(*,"(A)",ADVANCE="NO") "Enter the checksum of the "//
     c                       "turbine to display: "
              READ(*,"(A)") turbine_checksum

              bucket = calculate_bucket(turbine_id, NUM_TURBINE_BUCKETS)
              WRITE(bucket_str,"(I0.3)") bucket
              path = "data/turbines/" //
     c               bucket_str // "/" //
     c               TRIM(turbine_id) // ".DAT"

              OPEN(9,FILE=path,ACTION="READ",IOSTAT=ios)
              IF(ios .NE. 0) THEN
                  RETURN
              END IF

              READ(9,"(2A,I1,1A)",IOSTAT=ios) turbine%id,
     c                                        turbine%description,
     c                                        turbine%modelnumber,
     c                                        turbine%checksum
              IF(ios .NE. 0) THEN
                  WRITE(*,"(A)") "Error reading turbine details"
                  RETURN
              END IF

              IF (turbine_checksum .EQ. turbine%checksum) THEN
                  WRITE(*,"(2A)") "ID: ", TRIM(turbine%id)
                  WRITE(*,"(2A)") "Description: ",
     c                       TRIM(turbine%description)
                  WRITE(*,"(A,I1)") "Model number: ",
     c                       turbine%modelnumber
                  WRITE(*,"(A,A)") "Name: ",
     c            TRIM(modeldetails(turbine%modelnumber)%name)
                  WRITE(*,*) "Swep area: ",
     c            modeldetails(turbine%modelnumber)%swep_area

              ELSE
                  WRITE(*,"(A)") "Turbine Checksum was incorrect"
              END IF
              CLOSE(9)
          END SUBROUTINE show_turbine_details

          SUBROUTINE show_all_turbines()
              USE, INTRINSIC :: iso_fortran_env,
              USE, INTRINSIC :: iso_c_binding
              USE :: unix

              CHARACTER(len=512) :: entry_name, dir_path
              TYPE(c_dirent), pointer :: dirent_ptr
              TYPE(c_ptr) :: dir_ptr
              INTEGER :: rc, bucket, ios
              CHARACTER(len=3) :: bucket_str
              RECORD /TURBINE/ turbine

              ! Open directory.
              DO bucket = 0, NUM_TURBINE_BUCKETS - 1
                  WRITE(bucket_str,"(I0.3)") bucket
                  dir_path = "data/turbines/" //
     c                       bucket_str // c_null_char

                  dir_ptr = c_opendir(dir_path)

                  IF (.NOT. c_associated(dir_ptr)) THEN
                      CYCLE
                  END IF

                  DO
                      dirent_ptr => f_readdir(dir_ptr)

                      IF (.NOT. associated(dirent_ptr)) THEN
                          EXIT
                      END IF

                      IF (dirent_ptr%d_type .NE. DT_REG) THEN
                          CYCLE
                      END IF

                      CALL c_f_str_chars(dirent_ptr%d_name, entry_name)


                      OPEN(18,FILE="data/turbines/" // bucket_str //
     c                       "/" // TRIM(entry_name) // c_null_char,
     c                     ACTION="READ",IOSTAT=ios)
                      IF(ios .NE. 0) THEN
                          CYCLE
                      END IF

                      READ(18,"(2A,I1,1A)",IOSTAT=ios) turbine%id,
     c                                           turbine%description,
     c                                           turbine%modelnumber,
     c                                           turbine%checksum
                      CLOSE(18)
                      IF(ios .NE. 0) THEN
                          CYCLE
                      END IF

                      WRITE(*,"(3A)") turbine%id, ": ",
     c                                TRIM(turbine%description)
                  END DO

                  ! Close directory.
                  rc = c_closedir(dir_ptr)
              END DO
          END SUBROUTINE show_all_turbines

          CHARACTER(len=36) FUNCTION gen_uuid()
              CHARACTER(len=36) :: chars
              CHARACTER(len=36) :: uuid
              INTEGER :: counter, idx
              REAL :: r
              chars = "0123456789abcdefghijklmnopqrstuvwxyz"
              uuid = REPEAT("0",LEN(chars))
              DO counter = 1, 36
                  CALL RANDOM_NUMBER(r)
                  idx = CEILING(r*100000)
                  idx = MODULO(idx,36) + 1
                  uuid(counter:counter) = chars(idx:idx)
              END DO
              uuid(8:8) = '-'
              uuid(13:13) = '-'
              uuid(18:18) = '-'
              uuid(23:23) = '-'
              gen_uuid = uuid
              RETURN
          END FUNCTION gen_uuid

          FUNCTION turbine_id_exists(turbine_id)
              USE mod_bucket

              LOGICAL :: turbine_id_exists
              CHARACTER(len=36),INTENT(IN) :: turbine_id
              CHARACTER(len=3) :: bucket_str
              CHARACTER(len=512) :: path
              INTEGER :: bucket, ios

              bucket = calculate_bucket(turbine_id, NUM_TURBINE_BUCKETS)
              WRITE(bucket_str,"(I0.3)") bucket

              path = "data/turbines/" //
     c               bucket_str // "/" //
     c               TRIM(turbine_id) // ".DAT"

              OPEN(9,FILE=path,ACTION="READ",IOSTAT=ios)
              IF(ios .EQ. 0) THEN
                  CLOSE(9)
                  turbine_id_exists = .TRUE.
              ELSE
                  turbine_id_exists = .FALSE.
              END IF
          END FUNCTION

          SUBROUTINE register_turbine()
              USE mod_bucket

              RECORD /TURBINE/ turbine
              INTEGER :: logged_in, bucket, ios, i
              LOGICAL :: checksum_valid, id_exists
              CHARACTER(len=128) :: logged_in_username, path
              CHARACTER(len=3) :: bucket_str
              COMMON /session_status/ logged_in, logged_in_username

              ! Generate unique turbine ID
              DO i = 1, NUM_TURBINE_REGISTRATION_TRIES
                  turbine%id = gen_uuid()

                  id_exists = turbine_id_exists(turbine%id)
                  IF (.NOT. id_exists) THEN
                      EXIT
                  END IF
              END DO
              IF (id_exists) THEN
                  WRITE(*,"(A)") "Error: Could not generate unique " //
     c                           "turbine ID. Try again later."
                  RETURN
              END IF

              bucket = calculate_bucket(turbine%id, NUM_TURBINE_BUCKETS)
              WRITE(bucket_str,"(I0.3)") bucket
              CALL SYSTEM("mkdir --parents 'data/turbines/"
     c                                     // bucket_str // "'")

              WRITE(*,"(A)",ADVANCE="NO") "UUID is: "
              WRITE(*,"(A)") turbine%id
              WRITE(*,"(A)",ADVANCE="NO") "Description: "
              READ(*,"(A)") turbine%description
              WRITE(*,"(A)",ADVANCE="NO") "Model number: "
              READ(*,"(I1)") turbine%modelnumber
              WRITE(*,"(A)",ADVANCE="NO") "Checksum: "
              READ(*,"(A)") turbine%checksum

              checksum_valid = checksum_is_valid(turbine)
              IF (.NOT. checksum_valid) THEN
                WRITE(*,"(A)") "Error: Invalid checksum"
                  RETURN
              END IF
              
              path = "data/turbines/" //
     c               bucket_str // "/" // TRIM(turbine%id) // ".DAT"

              OPEN(9,FILE=path,ACTION="WRITE",IOSTAT=ios)
              IF(ios .NE. 0) THEN
                  WRITE(*,"(A)") "Error: Could not open turbine file"
                  RETURN
              END IF

              WRITE(9,"(2A,I1,1A)") turbine%id,
     c                              turbine%description,
     c                              turbine%modelnumber,
     c                              turbine%checksum
              CLOSE(9)
              WRITE(*,"(A)") "Turbine registered successfully"
          END SUBROUTINE register_turbine

          FUNCTION calculate_checksum(turbine)
              RECORD /TURBINE/,INTENT(IN) :: turbine
              CHARACTER(len=128) :: calculate_checksum, checksum
              CHARACTER(len=2) :: byte_buffer
              INTEGER :: i, j, a, b, c, value

              checksum = REPEAT("0", LEN(checksum))

              j = 1
              DO i = 1, LEN(turbine%id) / 2
                  a = ICHAR(turbine%id(i:i))
                  b = ICHAR(turbine%id(36 - i:36 - i))
                  c = INT(get_diffusion_val(MOD(a + b, 256) + 1))
                  !value = iEOR(c,IEOR(i, IEOR(a,
     c            !    IEOR(b, turbine%modelnumber))))
                  value = iEOR(b,IEOR(i, IEOR(a,
     c            IEOR(b, turbine%modelnumber)))) 
                  WRITE(byte_buffer,"(Z0.2)") value
                  checksum(j:j + 1) = byte_buffer
                  j = j + 2
              END DO

              calculate_checksum = checksum
          END FUNCTION calculate_checksum

          FUNCTION checksum_is_valid(turbine)
              RECORD /TURBINE/,INTENT(IN) :: turbine
              LOGICAL :: checksum_is_valid
              CHARACTER(len=128) :: expected_checksum

              expected_checksum = calculate_checksum(turbine)

              IF (turbine%checksum .EQ. expected_checksum) THEN
                  checksum_is_valid = .TRUE.
              ELSE
                  checksum_is_valid = .FALSE.
              END IF
          END FUNCTION checksum_is_valid
      END MODULE MOD_TURBINE
