import { transform, isEqual, isObject } from 'lodash-es';

// ref: https://gist.github.com/Yimiprod/7ee176597fef230d1451
export function difference(object: object, base: object): object {
  function diff(object: object, base: object) {
    return transform(object, (result: object, value: any, key: string) => {
      const baseValue = Reflect.get(base, key);
      if (!isEqual(value, baseValue)) {
        Reflect.set(
          result,
          key,
          isObject(value) && isObject(baseValue)
            ? diff(value, baseValue)
            : value
        );
      }
    });
  }
  return diff(object, base);
}
