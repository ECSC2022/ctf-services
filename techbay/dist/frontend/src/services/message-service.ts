export interface MessageService {
  danger: (options: { text: string; duration: number }) => void;
  success: (options: { text: string; duration: number }) => void;
  primary: (options: { text: string; duration: number }) => void;
  warning: (options: { text: string; duration: number }) => void;
}
