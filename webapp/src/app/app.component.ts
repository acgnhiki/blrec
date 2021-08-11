import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnDestroy,
} from '@angular/core';
import { Router, NavigationEnd, NavigationStart } from '@angular/router';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';

import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements OnDestroy {
  title = 'B 站直播录制';
  theme: 'light' | 'dark' = 'light';

  loading = false;
  collapsed = false;
  useDrawer = false;
  destroyed = new Subject<void>();

  constructor(
    router: Router,
    changeDetector: ChangeDetectorRef,
    breakpointObserver: BreakpointObserver
  ) {
    router.events.subscribe((event) => {
      if (event instanceof NavigationStart) {
        this.loading = true;
        // close the drawer
        if (this.useDrawer) {
          this.collapsed = true;
        }
      } else if (event instanceof NavigationEnd) {
        this.loading = false;
      }
    });

    // use drawer as side nav for x-small device
    breakpointObserver
      .observe(Breakpoints.XSmall)
      .pipe(takeUntil(this.destroyed))
      .subscribe((state) => {
        this.useDrawer = state.matches;
        // ensure the drawer is closed
        if (this.useDrawer) {
          this.collapsed = true;
        }
        changeDetector.markForCheck();
      });

    // display task cards as many as possible
    // max-width: card-width(400px) * 2 + gutter(12px) + padding(12px) * 2 + sidenav(200px)
    breakpointObserver
      .observe('(max-width: 1036px)')
      .pipe(takeUntil(this.destroyed))
      .subscribe((state) => {
        this.collapsed = state.matches;
        changeDetector.markForCheck();
      });
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }
}
