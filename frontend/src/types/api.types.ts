export interface ApiError {
    detail: string;
}

export interface ApiResponse<T> {
    data: T;
    message?: string;
    success?: boolean;
}
