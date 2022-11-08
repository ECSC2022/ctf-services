
      SUBROUTINE show_banner()
          WRITE(*,"(A)") "=== TURBINE MANAGEMENT ==="
      END SUBROUTINE show_banner

      SUBROUTINE print_menu()
          INTEGER :: logged_in
          CHARACTER(len=128) logged_in_username
          COMMON /session_status/ logged_in, logged_in_username

          WRITE(*,"(A)") "0. Exit"
          WRITE(*,"(A)") "1. Register user"
          WRITE(*,"(A)") "2. Login"
          IF (logged_in .EQ. 1) THEN
              WRITE(*,"(A)") "3. Show user details"
              WRITE(*,"(A)") "4. Show turbine details"
              WRITE(*,"(A)") "5. Register turbine"
              WRITE(*,"(A)") "6. Calculate capacity"
          END IF
          WRITE(*,"(A)",ADVANCE="NO") "Select an option: "
      END SUBROUTINE print_menu

      PROGRAM turbines
          USE mod_consumption
          USE mod_turbine
          USE mod_user
        
          INTEGER :: chosen_menu_option
          INTEGER :: logged_in
          CHARACTER(len=128) :: logged_in_username
          RECORD /MODELDETAILS/ modeldetails(5)
          COMMON /session_status/ logged_in, logged_in_username
          COMMON /model_details/ modeldetails

          modeldetails(1)%modelnumber = 1
          modeldetails(1)%name = "SUPER POWERPLANT 1"
          modeldetails(1)%swep_area = 11.7

          modeldetails(2)%modelnumber = 2
          modeldetails(2)%name = "SUPER POWERPLANT 2"
          modeldetails(3)%swep_area = 50

          modeldetails(3)%modelnumber = 3
          modeldetails(3)%name = "SUPER POWERPLANT 3"
          modeldetails(3)%swep_area = 100

          modeldetails(4)%modelnumber = 4
          modeldetails(4)%name = "SUPER POWERPLANT 4"
          modeldetails(4)%swep_area = 150

          modeldetails(5)%modelnumber = 5
          modeldetails(5)%name = "SUPER POWERPLANT 5"
          modeldetails(5)%swep_area = 170

          CALL show_banner()

          DO
              CALL print_menu()
              READ(*,*) chosen_menu_option

              SELECT CASE(chosen_menu_option)
                  CASE (0)
                      CALL EXIT()
                  CASE (1)
                      CALL register_user()
                  CASE (2)
                      CALL login()
                  CASE (3)
                      IF (logged_in .NE. 1) THEN
                          WRITE(*,"(A)") "You need to log in first"
                      ELSE
                          CALL show_user_details()
                      END IF
                  CASE (4)
                      IF (logged_in .NE. 1) THEN
                          WRITE(*,"(A)") "You need to log in first"
                      ELSE
                          CALL show_turbine_details()
                      END IF
                  CASE (5)
                      IF (logged_in .NE. 1) THEN
                          WRITE(*,"(A)") "You need to log in first"
                      ELSE
                          CALL register_turbine()
                      END IF
                  CASE (6)
                      IF (logged_in .NE. 1) THEN
                         WRITE(*,"(A)") "You need to log in first"
                      ELSE
                          CALL calculate_turbine_capacity()
                  END IF
                  CASE DEFAULT
                      WRITE(*,"(A)") "Unknown option"
              END SELECT

              WRITE(*,*) NEW_LINE("A")
          END DO
      END PROGRAM turbines
