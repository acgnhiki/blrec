// from https://medium.com/front-end-weekly/handling-scrolling-on-angular-router-transitions-e7652e57d964
import { NavigationEnd, NavigationStart } from "@angular/router";

/**
 * Service that handles scrolling back to top if/when needed, depending on the configured strategies and route config.
 * Can be configured through route data, by defining the "scrollBehavior" key and setting it to a valid {RouteScrollBehaviour} value
 * References
 * https://www.bennadel.com/blog/3534-restoring-and-resetting-the-scroll-position-using-the-navigationstart-event-in-angular-7-0-4.htm
 *   Potential for improvement from there: listen to scroll events on the DOM
 * https://medium.com/angular-in-depth/reactive-scroll-position-restoration-with-rxjs-792577f842c
 * https://medium.com/@samisalamiger/great-article-f4f642b134ab
 */
export interface IRouterScrollService {
  /**
   * Provide the DOM element corresponding to the main viewport.
   * That viewport is the one that will be scrolled
   */
  setCustomViewportToScroll(viewport: HTMLElement): void;

  /**
   * Disable scrolling the default viewport
   */
  disableScrollDefaultViewport(): void;

  /**
   * Enable scrolling the default viewport (enabled by default)
   */
  enableScrollDefaultViewPort(): void;

  /**
   * Add a strategy that applies before navigation for a partial route
   * @param partialRoute the partial route to match
   * @param behaviour the desired behavior
   */
  addStrategyOnceBeforeNavigationForPartialRoute(partialRoute: string, behaviour: RouteScrollBehaviour): void;

  /**
   * Add a strategy for a partial route
   * @param partialRoute the partial route to match
   * @param behaviour the desired behavior
   */
  addStrategyForPartialRoute(partialRoute: string, behaviour: RouteScrollBehaviour): void;

  /**
   * Remove a strategy for a partial route
   * @param partialRoute the partial route to remove strategies for
   */
  removeStrategyForPartialRoute(partialRoute: string): void;
}

/**
 * Scroll position restore
 */
export interface ScrollPositionRestore {
  /**
   * Which event to match
   */
  event: NavigationStart | NavigationEnd;
  /**
   * Used to keep track of the known positions.
   * The key is the id of the entry (according to the route ids)
   * The value is the scroll position. Any is used because there are different representations
   */
  positions: Record<string, any>;
  /**
   * Trigger to react to
   * Imperative: e.g., user clicked on a link
   * Popstate: e.g., browser back button
   * Hashchange: e.g., change in the URL fragment
   */
  trigger: "imperative" | "popstate" | "hashchange" | undefined;
  /**
   * Id to restore
   */
  idToRestore: number;
  /**
   * The route's data (if any defined)
   */
  routeData?: CustomRouteData;
}

/**
 * Defines a strategy to handle route scrolling.
 */
export interface RouteScrollStrategy {
  /**
   * Partial route path
   */
  partialRoute: string;
  /**
   * Associated behavior
   */
  behaviour: RouteScrollBehaviour;
  /**
   * Whether it should be applied before navigation (default is after)
   */
  onceBeforeNavigation?: boolean;
}

/**
 * Defines the possible route scroll behaviors
 */
export enum RouteScrollBehaviour {
  KEEP_POSITION = "KEEP_POSITION",
  GO_TO_TOP = "GO_TO_TOP",
}

/**
 * Extends the default type of Angular to be more prescriptive
 */
export interface CustomRouteData {
  /**
   * Scroll behavior when navigating to this route
   */
  scrollBehavior?: RouteScrollBehaviour;
}

/**
 * Define a set of routes for the router.
 * Usually one instance defined per module in the app.
 */
export type CustomRoutes = CustomRouteData[];
