import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WaveGraphComponent } from './wave-graph.component';

describe('WaveGraphComponent', () => {
  let component: WaveGraphComponent;
  let fixture: ComponentFixture<WaveGraphComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WaveGraphComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(WaveGraphComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
