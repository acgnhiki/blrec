export type Mutable<Type> = {
  -readonly [Property in keyof Type]: Type[Property];
}

export type Nullable<Type> = {
  [Property in keyof Type]: Type[Property] | null;
};

export type PartialDeep<Type> = {
  [Property in keyof Type]?: Partial<Type[Property]> | undefined;
};
