// from https://medium.com/front-end-weekly/handling-scrolling-on-angular-router-transitions-e7652e57d964
import { ActivatedRoute, NavigationEnd, NavigationStart, Router } from "@angular/router";
import { Injectable, OnDestroy } from "@angular/core";
import { ViewportScroller } from "@angular/common";
import { filter, observeOn, scan } from "rxjs/operators";
import { asyncScheduler, Subscription } from "rxjs";
import {
  IRouterScrollService,
  RouteScrollBehaviour,
  RouteScrollStrategy,
  ScrollPositionRestore,
} from "./router-scroll.service.intf";
import { NGXLogger } from "ngx-logger";
import { environment } from 'src/environments/environment';

const componentName = "RouterScrollService";

const defaultViewportKey = `defaultViewport`;
const customViewportKey = `customViewport`;

@Injectable({
  providedIn: 'root',
})
export class RouterScrollService implements IRouterScrollService, OnDestroy {
  private readonly scrollPositionRestorationSubscription: Subscription | null;

  /**
   * Queue of strategies to add
   */
  private addQueue: RouteScrollStrategy[] = [];
  /**
   * Queue of strategies to add for onBeforeNavigation
   */
  private addBeforeNavigationQueue: RouteScrollStrategy[] = [];
  /**
   * Queue of strategies to remove
   */
  private removeQueue: string[] = [];
  /**
   * Registered strategies
   */
  private routeStrategies: RouteScrollStrategy[] = [];
  /**
   * Whether the default viewport should be scrolled if/when needed
   */
  private scrollDefaultViewport = true;
  /**
   * Custom viewport to scroll if/when needed
   */
  private customViewportToScroll: HTMLElement | null = null;

  constructor(
    private readonly router: Router,
    private readonly activatedRoute: ActivatedRoute,
    private readonly viewportScroller: ViewportScroller,
    private readonly logger: NGXLogger,
  ) {
    if (environment.traceRouterScrolling) {
      this.logger.trace(`${componentName}:: constructor`);
    }

    if (environment.traceRouterScrolling) {
      this.logger.trace(`${componentName}:: Subscribing to router events`);
    }

    const scrollPositionRestore$ = this.router.events.pipe(
      filter((event: any) => event instanceof NavigationStart || event instanceof NavigationEnd),
      // Accumulate the scroll positions
      scan<NavigationEnd | NavigationStart, ScrollPositionRestore>((acc, event) => {
        if (environment.traceRouterScrolling) {
          this.logger.trace(`${componentName}:: Updating the known scroll positions`);
        }
        const positions: Record<string, any> = {
          ...acc.positions, // Keep the previously known positions
        };

        if (event instanceof NavigationStart && this.scrollDefaultViewport) {
          if (environment.traceRouterScrolling) {
            this.logger.trace(`${componentName}:: Storing the scroll position of the default viewport`);
          }
          positions[`${event.id}-${defaultViewportKey}`] = this.viewportScroller.getScrollPosition();
        }

        if (event instanceof NavigationStart && this.customViewportToScroll) {
          if (environment.traceRouterScrolling) {
            this.logger.trace(`${componentName}:: Storing the scroll position of the custom viewport`);
          }
          positions[`${event.id}-${customViewportKey}`] = this.customViewportToScroll.scrollTop;
        }

        const retVal: ScrollPositionRestore = {
          event,
          positions,
          trigger: event instanceof NavigationStart ? event.navigationTrigger : acc.trigger,
          idToRestore:
            (event instanceof NavigationStart && event.restoredState && event.restoredState.navigationId + 1) ||
            acc.idToRestore,
          routeData: this.activatedRoute.firstChild?.routeConfig?.data,
        };

        return retVal;
      }),
      filter((scrollPositionRestore: ScrollPositionRestore) => !!scrollPositionRestore.trigger),
      observeOn(asyncScheduler),
    );

    this.scrollPositionRestorationSubscription = scrollPositionRestore$.subscribe(
      (scrollPositionRestore: ScrollPositionRestore) => {
        const existingStrategy = this.routeStrategies.find(
          (strategy) => scrollPositionRestore.event.url.indexOf(strategy.partialRoute) > -1,
        );

        const existingStrategyWithKeepScrollPositionBehavior =
          (existingStrategy && existingStrategy.behaviour === RouteScrollBehaviour.KEEP_POSITION) || false;
        const routeDataWithKeepScrollPositionBehavior =
          (scrollPositionRestore.routeData &&
            scrollPositionRestore.routeData.scrollBehavior &&
            scrollPositionRestore.routeData.scrollBehavior === RouteScrollBehaviour.KEEP_POSITION) ||
          false;

        const shouldKeepScrollPosition =
          existingStrategyWithKeepScrollPositionBehavior || routeDataWithKeepScrollPositionBehavior;

        if (scrollPositionRestore.event instanceof NavigationEnd) {
          this.processRemoveQueue(this.removeQueue);

          // Was this an imperative navigation? This helps determine if we're moving forward through a routerLink, a back button click, etc
          // Reference: https://www.bennadel.com/blog/3533-using-router-events-to-detect-back-and-forward-browser-navigation-in-angular-7-0-4.htm
          const imperativeTrigger =
            (scrollPositionRestore.trigger && "imperative" === scrollPositionRestore.trigger) || false;

          // Should scroll to the top if
          // no strategy or strategy with behavior different than keep position
          // OR no route data or route data with behavior different than keep position
          // OR imperative
          // Reference: https://medium.com/javascript-everyday/angular-imperative-navigation-fbab18a25d8b

          // Decide whether we should scroll back to top or not
          const shouldScrollToTop = !shouldKeepScrollPosition || imperativeTrigger;

          if (environment.traceRouterScrolling) {
            this.logger.trace(
              `${componentName}:: Existing strategy with keep position behavior? `,
              existingStrategyWithKeepScrollPositionBehavior,
            );
            this.logger.trace(
              `${componentName}:: Route data with keep position behavior? `,
              routeDataWithKeepScrollPositionBehavior,
            );
            this.logger.trace(`${componentName}:: Imperative trigger? `, imperativeTrigger);
            this.logger.debug(`${componentName}:: Should scroll? `, shouldScrollToTop);
          }

          if (shouldScrollToTop) {
            if (this.scrollDefaultViewport) {
              if (environment.traceRouterScrolling) {
                this.logger.debug(`${componentName}:: Scrolling the default viewport`);
              }
              this.viewportScroller.scrollToPosition([0, 0]);
            }
            if (this.customViewportToScroll) {
              if (environment.traceRouterScrolling) {
                this.logger.debug(`${componentName}:: Scrolling a custom viewport: `, this.customViewportToScroll);
              }
              this.customViewportToScroll.scrollTop = 0;
            }
          } else {
            if (environment.traceRouterScrolling) {
              this.logger.debug(`${componentName}:: Not scrolling`);
            }

            if (this.scrollDefaultViewport) {
              this.viewportScroller.scrollToPosition(
                scrollPositionRestore.positions[`${scrollPositionRestore.idToRestore}-${defaultViewportKey}`],
              );
            }

            if (this.customViewportToScroll) {
              this.customViewportToScroll.scrollTop =
                scrollPositionRestore.positions[`${scrollPositionRestore.idToRestore}-${customViewportKey}`];
            }
          }

          this.processRemoveQueue(
            this.addBeforeNavigationQueue.map((strategy) => strategy.partialRoute),
            true,
          );
          this.processAddQueue(this.addQueue);
          this.addQueue = [];
          this.removeQueue = [];
          this.addBeforeNavigationQueue = [];
        } else {
          this.processAddQueue(this.addBeforeNavigationQueue);
        }
      },
    );
  }

  addStrategyOnceBeforeNavigationForPartialRoute(partialRoute: string, behaviour: RouteScrollBehaviour): void {
    if (environment.traceRouterScrolling) {
      this.logger.trace(
        `${componentName}:: Adding a strategy once for before navigation towards [${partialRoute}]: `,
        behaviour,
      );
    }
    this.addBeforeNavigationQueue.push({
      partialRoute: partialRoute,
      behaviour: behaviour,
      onceBeforeNavigation: true,
    });
  }

  addStrategyForPartialRoute(partialRoute: string, behaviour: RouteScrollBehaviour): void {
    if (environment.traceRouterScrolling) {
      this.logger.trace(`${componentName}:: Adding a strategy for partial route: [${partialRoute}]`, behaviour);
    }
    this.addQueue.push({ partialRoute: partialRoute, behaviour: behaviour });
  }

  removeStrategyForPartialRoute(partialRoute: string): void {
    if (environment.traceRouterScrolling) {
      this.logger.trace(`${componentName}:: Removing strategory for: [${partialRoute}]: `);
    }
    this.removeQueue.push(partialRoute);
  }

  setCustomViewportToScroll(viewport: HTMLElement): void {
    if (environment.traceRouterScrolling) {
      this.logger.trace(`${componentName}:: Setting a custom viewport to scroll: `, viewport);
    }
    this.customViewportToScroll = viewport;
  }

  disableScrollDefaultViewport(): void {
    if (environment.traceRouterScrolling) {
      this.logger.trace(`${componentName}:: Disabling scrolling the default viewport`);
    }
    this.scrollDefaultViewport = false;
  }

  enableScrollDefaultViewPort(): void {
    if (environment.traceRouterScrolling) {
      this.logger.trace(`${componentName}:: Enabling scrolling the default viewport`);
    }
    this.scrollDefaultViewport = true;
  }

  processAddQueue(queue: any) {
    for (const partialRouteToAdd of queue) {
      const pos = this.routeStrategyPosition(partialRouteToAdd.partialRoute);
      if (pos === -1) {
        this.routeStrategies.push(partialRouteToAdd);
      }
    }
  }

  processRemoveQueue(queue: any, removeOnceBeforeNavigation = false) {
    for (const partialRouteToRemove of queue) {
      const pos = this.routeStrategyPosition(partialRouteToRemove);
      if (!removeOnceBeforeNavigation && pos > -1 && this.routeStrategies[pos].onceBeforeNavigation) {
        continue;
      }
      if (pos > -1) {
        this.routeStrategies.splice(pos, 1);
      }
    }
  }

  routeStrategyPosition(partialRoute: string) {
    return this.routeStrategies.map((strategy) => strategy.partialRoute).indexOf(partialRoute);
  }

  ngOnDestroy(): void {
    if (environment.traceRouterScrolling) {
      this.logger.trace(`${componentName}:: ngOnDestroy`);
    }
    if (this.scrollPositionRestorationSubscription) {
      this.scrollPositionRestorationSubscription.unsubscribe();
    }
  }
}
