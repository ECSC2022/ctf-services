export declare function instantiate(pck: string, struct: string): i64;
export declare function invoke(
    handler: i64,
    method: string,
    parameters: string
): string;
export declare function retrieve(
    handler: i64,
    prop: string
): string;
