      SUBROUTINE UEXTERNALDB(LOP,LRESTART,TIME,DTIME,KSTEP,KINC)
C
      INCLUDE 'ABA_PARAM.INC'
C
      DIMENSION TIME(2)
      CHARACTER(len = 80)::msg          
      INTEGER::ERROR, ALIVE
      CHARACTER(len = 80)::filename
      
C     define the stress array elemnt number stres 1 2 3
      real::stress_import(493117,4) 
      
C     make that stress array common to all subroutines
      common stress_import
C
C     Set this subroutine to only happen once at the start
      LOP=0
C     define the file name and path for the stress array to be loaded from
    filename = '\sigma.txt'
C     load the stress array as 100
      INQUIRE(FILE=filename,EXIST=ALIVE)
      PRINT*,ALIVE
      OPEN(100 , FILE = filename, ACTION = 'READ',
     1STATUS='OLD')
      IF (ERROR.EQ.0) THEN
          DO i=1,493117
              READ(100 , *), stress_import(i,:)
          END DO 
      ELSE
          PRINT*,ERROR
      END IF
      CLOSE(100)

      
      RETURN
      END
      
      
      SUBROUTINE SIGINI(SIGMA,COORDS,NTENS,NCRDS,NOEL,NPT,LAYER, KSPT,LREBAR,NAMES)
      
      INCLUDE 'ABA_PARAM.INC'
      
      DIMENSION SIGMA(NTENS), COORDS(NCRDS)
      CHARACTER NAMES(2)*80
      INTEGER row, RECNO, i
C     define the stress array elemnt number stres 1 2 3
      REAL::stress_import(493117, 4)
C     make that stress array common to all subroutines
      COMMON stress_import
C     set a conunter equal to the element number, diffrent meshes may need a diffrent counter
      RECNO = NOEL
C     loop over every possible element number, when the element number and the loop iteration match load that line of the stress array
C     SIGMA4,5 and 6 are 0 as no shear stresses predected by the current inported model
      DO i=1,493117
        IF( stress_import(i,1).EQ.RECNO) THEN
        
          SIGMA(1) = stress_import(i,2)
          SIGMA(2) = stress_import(i,3)
          SIGMA(3) = stress_import(i,4)
          SIGMA(4) = 0
          SIGMA(5) = 0
          SIGMA(6) = 0
C         print for log file to monitor it running
          PRINT*,'EL Row S123', NOEL, i, SIGMA(1), SIGMA(2), SIGMA(3)
          
        END IF
     END DO

      
      RETURN
      END SUBROUTINE SIGINI