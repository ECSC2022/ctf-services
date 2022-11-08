      MODULE mod_user
          INTEGER :: NUM_USER_BUCKETS = 256
          INTEGER :: MIN_USERNAME_LENGTH = 6
          INTEGER :: MAX_USERNAME_LENGTH = 128
          INTEGER :: MIN_PASSWORD_LENGTH = 6
          INTEGER :: MAX_PASSWORD_LENGTH = 128

          STRUCTURE /USER/
              CHARACTER(len=128) username
              CHARACTER(len=128) password
          END STRUCTURE

          CONTAINS

          FUNCTION username_already_registered(username)
              USE mod_bucket

              LOGICAL :: username_already_registered
              INTEGER :: ios, bucket
              CHARACTER(len=128),INTENT(IN) :: username
              CHARACTER(len=3) :: bucket_str

              bucket = calculate_bucket(username, NUM_USER_BUCKETS)
              WRITE(bucket_str,"(I0.3)") bucket

              OPEN(9,FILE="data/users/" // bucket_str // "/"
     c                                  // TRIM(username)
     c                                  // ".DAT",
     c             ACTION="READ",IOSTAT=ios)
              IF(ios .EQ. 0) THEN
                  username_already_registered = .TRUE.
              ELSE
                  username_already_registered = .FALSE.
              END IF
              CLOSE(9)

          END FUNCTION username_already_registered

          SUBROUTINE register_user()
              USE mod_bucket

              RECORD /USER/ user
              LOGICAL :: username_exists, valid_username_chars
              CHARACTER(len=128) :: trimmed_username
              CHARACTER(len=3) :: bucket_str
              INTEGER :: c, i, bucket

              WRITE(*,"(A)",ADVANCE="NO") "Username: "
              READ(*,"(A)") user%username
              WRITE(*,"(A)",ADVANCE="NO") "Password: "
              READ(*,"(A)") user%password

              IF (LEN(TRIM(user%username)) .LT.
     c              MIN_USERNAME_LENGTH) THEN
                  WRITE(*,"(A,I2,A)") "Error: Username must be "//
     c                                "at least ",
     c                                MIN_USERNAME_LENGTH,
     c                                " characters long"
                  RETURN
              END IF

              valid_username_chars = .TRUE.
              trimmed_username = TRIM(user%username)
              DO i = 1, LEN_TRIM(trimmed_username)
                  c = ICHAR(trimmed_username(i:i))
                  IF (c .GE. ICHAR("a") .AND. c .LE. ICHAR("z")) THEN
                      CYCLE
                  END IF
                  IF (c .GE. ICHAR("0") .AND. c .LE. ICHAR("9")) THEN
                      CYCLE
                  END IF
                  IF (c .EQ. ICHAR("-")) THEN
                      CYCLE
                  END IF
                  valid_username_chars = .FALSE.
                  EXIT
              END DO
              IF (.NOT. valid_username_chars) THEN
                  WRITE(*,"(A)") "Invalid characters in username."
                  WRITE(*,"(A)") "Format: [a-z0-9-]{6,64}"
                  RETURN
              END IF

              IF (LEN(TRIM(user%password)) .LT.
     c              MIN_PASSWORD_LENGTH) THEN
                  WRITE(*,"(A,I2,A)") "Error: Password must be "//
     c                                "at least ",
     c                                MIN_PASSWORD_LENGTH,
     c                                " characters long"
                  RETURN
              END IF

              username_exists =
     c            username_already_registered(user%username)
              IF (username_exists) THEN
                  WRITE(*,"(A)") "Error: Username already in use"
                  RETURN
              END IF

              bucket = calculate_bucket(user%username, NUM_USER_BUCKETS)
              WRITE(bucket_str,"(I0.3)") bucket

              CALL SYSTEM("mkdir --parents 'data/users/"
     c                                      // bucket_str // "'")
              OPEN(9,FILE="data/users/" // bucket_str // "/"
     c                                  // TRIM(user%username)
     c                                  // ".DAT",
     c             ACTION="WRITE",POSITION="APPEND")
              WRITE(9,"(2A)") user%username, user%password
              CLOSE(9)

              WRITE(*,"(A)") "User registered"
          END SUBROUTINE register_user

          SUBROUTINE login()
              USE mod_bucket

              RECORD /USER/ input_user, file_user
              INTEGER :: ios
              INTEGER :: bucket = 0
              INTEGER :: user_found = 0
              INTEGER :: logged_in
              CHARACTER(len=3) bucket_str
              CHARACTER(len=128) logged_in_username
              COMMON /session_status/ logged_in, logged_in_username

              WRITE(*,"(A)",ADVANCE="NO") "Username: "
              READ(*,"(A)") input_user%username
              WRITE(*,"(A)",ADVANCE="NO") "Password: "
              READ(*,"(A)") input_user%password

              bucket = calculate_bucket(input_user%username,
     c                                  NUM_USER_BUCKETS)
              WRITE(bucket_str,"(I0.3)") bucket
              logged_in = 0

              ! Check if user file exists
              OPEN(9,FILE="data/users/" // bucket_str // "/"
     c                                  // TRIM(input_user%username)
     c                                  // ".DAT",
     c             ACTION="READ",IOSTAT=ios)
              IF(ios .NE. 0) THEN
                  WRITE(*,"(A)") "Login failed"
                  RETURN
              END IF

              ! Read user information and check if input matches
              READ(9,"(2A)",IOSTAT=ios) file_user%username,
     c                                  file_user%password
              IF(ios .EQ. 0) THEN
                  IF(file_user%username .EQ. input_user%username .AND.
     c               file_user%password .EQ. input_user%password) THEN
                      user_found = 1
                  END IF
              END IF
              CLOSE(9)

              ! If a valid user was found, store the session information in global variables
              IF (user_found .EQ. 1) THEN
                  logged_in = user_found
                  logged_in_username = input_user%username
                  WRITE(*,"(A)") "Logged in successfully"
              ELSE
                  WRITE(*,"(A)") "Login failed"
              END IF
          END SUBROUTINE login

          SUBROUTINE show_user_details()
              USE mod_bucket

              INTEGER :: logged_in, bucket, ios
              CHARACTER(len=128) :: logged_in_username
              CHARACTER(len=3) :: bucket_str
              RECORD /USER/ file_user
              COMMON /session_status/ logged_in, logged_in_username

              bucket = calculate_bucket(logged_in_username,
     c                                  NUM_USER_BUCKETS)
              WRITE(bucket_str,"(I0.3)") bucket

              OPEN(9,FILE="data/users/" // bucket_str // "/"
     c                                  // TRIM(logged_in_username)
     c                                  // ".DAT",
     c             ACTION="READ",IOSTAT=ios)
              IF(ios .NE. 0) THEN
                  WRITE(*,"(A)") "Reading user information failed"
                  RETURN
              END IF

              ! Read user information and check if input matches
              READ(9,"(2A)",IOSTAT=ios) file_user%username,
     c                                  file_user%password
              CLOSE(9)
              IF(ios .NE. 0) THEN
                  WRITE(*,"(A)") "Reading user information failed"
                  RETURN
              END IF

              WRITE(*,"(4A)") "User: ",
     c                        TRIM(file_user%username),
     c                        " / ",
     c                        TRIM(file_user%password)
          END SUBROUTINE show_user_details
      END MODULE mod_user
