export interface ResponseMessage {
  readonly code: number;
  readonly message: string
  readonly data?: {
    readonly [key: string]: any
  }
}
