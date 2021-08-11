import { ComponentFixture, TestBed } from '@angular/core/testing';

import { InfoListComponent } from './info-list.component';

describe('InfoListComponent', () => {
  let component: InfoListComponent;
  let fixture: ComponentFixture<InfoListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ InfoListComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(InfoListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
